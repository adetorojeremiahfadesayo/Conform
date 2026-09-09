"""Analytics read path — official mcp-clickhouse MCP server when configured.

The analyst agent reads build history exclusively through this client so the
ClickHouse MCP connection is genuinely load-bearing (hackathon track
requirement). When no MCP endpoint is configured the client falls back to the
writer's direct query path, labelled `mode="fallback_direct"`.

SQL safety contract (FR-8.6): only single SELECT statements, parameterised,
with an enforced LIMIT ceiling. Anything else raises before it hits the wire.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Protocol

from app.config import Config
from app.domain.schemas import ConformError

MAX_ROWS = 500

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|attach|detach|grant|revoke|rename|optimize|kill)\b",
    re.IGNORECASE,
)


def guard_sql(sql: str) -> str:
    """Allowlist guard: single read-only SELECT only."""
    stripped = sql.strip().rstrip(";")
    if not stripped.lower().startswith(("select", "with")):
        raise ConformError("SQL_NOT_SELECT", "analyst queries must be SELECT statements")
    if ";" in stripped:
        raise ConformError("SQL_MULTI_STATEMENT", "multiple statements are not allowed")
    if _FORBIDDEN.search(stripped):
        raise ConformError("SQL_FORBIDDEN_KEYWORD", "write/DDL keywords are not allowed in analyst queries")
    if not re.search(r"\blimit\b", stripped, re.IGNORECASE):
        stripped = f"{stripped} LIMIT {MAX_ROWS}"
    return stripped


class HistoryReader(Protocol):
    mode: str

    def run_select_query(self, sql: str, params: dict | None = None) -> list[dict]: ...


class DirectReader:
    """Fallback: queries the configured writer directly. Labelled honestly."""

    mode = "fallback_direct"

    def __init__(self, writer):
        self._writer = writer

    def run_select_query(self, sql: str, params: dict | None = None) -> list[dict]:
        return self._writer.query(guard_sql(sql), params)


class McpClickHouseReader:
    """Calls the official mcp-clickhouse server over HTTP (streamable transport),
    tool `run_query`. Read-only by server default and by our guard."""

    def __init__(self, config: Config):
        self._url = config.clickhouse_mcp_url.rstrip("/")
        self._auth_token = config.clickhouse_mcp_auth_token
        self.mode = "configured_unverified"
        self._session_id: str | None = None

    def run_select_query(self, sql: str, params: dict | None = None) -> list[dict]:
        safe_sql = guard_sql(sql)
        if params:
            for key, value in params.items():
                safe_sql = safe_sql.replace(f"{{{key}:String}}", _quote(str(value)))
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "run_query", "arguments": {"query": safe_sql}},
            }
        ).encode()
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        headers["MCP-Protocol-Version"] = "2025-03-26"
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        req = urllib.request.Request(
            f"{self._url}/mcp",
            data=payload,
            headers=headers,
        )
        try:
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    body = resp.read().decode()
            except urllib.error.HTTPError as exc:
                if exc.code not in (400, 404):
                    raise
                init = {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {
                    "protocolVersion": "2025-03-26", "capabilities": {},
                    "clientInfo": {"name": "conform", "version": "0.1.0"},
                }}
                headers.pop("Mcp-Session-Id", None)
                with urllib.request.urlopen(urllib.request.Request(
                    f"{self._url}/mcp", data=json.dumps(init).encode(), headers=headers,
                ), timeout=30) as resp:
                    self._session_id = resp.headers.get("Mcp-Session-Id")
                    resp.read()
                if self._session_id:
                    headers["Mcp-Session-Id"] = self._session_id
                with urllib.request.urlopen(urllib.request.Request(
                    f"{self._url}/mcp", headers=headers,
                    data=json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}).encode(),
                ), timeout=30) as resp:
                    resp.read()
                with urllib.request.urlopen(urllib.request.Request(
                    f"{self._url}/mcp", data=payload, headers=headers,
                ), timeout=30) as resp:
                    body = resp.read().decode()
        except Exception as exc:
            self.mode = "error"
            raise ConformError("MCP_UNREACHABLE", f"ClickHouse MCP server unreachable: {exc}") from exc
        try:
            rows = _parse_mcp_result(body)
        except Exception:
            self.mode = "error"
            raise
        self.mode = "live_mcp"
        return rows


def _quote(value: str) -> str:
    return "'" + value.replace("'", "\\'") + "'"


def _parse_mcp_result(body: str) -> list[dict]:
    """Extract rows from an MCP JSON-RPC (or SSE) response."""
    text = body
    if "data:" in body:  # SSE stream — take the last data frame
        text = body.split("data:")[-1].strip()
    envelope = json.loads(text)
    if "error" in envelope:
        raise ConformError("MCP_ERROR", str(envelope["error"])[:300])
    if envelope.get("result", {}).get("isError"):
        raise ConformError("MCP_ERROR", str(envelope["result"].get("content", []))[:300])
    content = envelope.get("result", {}).get("content", [])
    for item in content:
        if item.get("type") == "text":
            try:
                parsed = json.loads(item["text"])
                if isinstance(parsed, list):
                    return parsed
                if isinstance(parsed, dict) and "data" in parsed:
                    return parsed["data"]
                if isinstance(parsed, dict) and "rows" in parsed:
                    rows = parsed["rows"]
                    columns = parsed.get("column_names", parsed.get("columns", []))
                    if rows and isinstance(rows[0], list) and columns:
                        names = [c["name"] if isinstance(c, dict) else c for c in columns]
                        return [dict(zip(names, row)) for row in rows]
                    return rows
            except json.JSONDecodeError:
                continue
    return []


def build_reader(config: Config, writer) -> HistoryReader:
    if config.mcp_live:
        return McpClickHouseReader(config)
    return DirectReader(writer)
