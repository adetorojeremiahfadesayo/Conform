"""Tests for app.store.mcp_client — McpClickHouseReader with mocked HTTP."""

from __future__ import annotations

import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.domain.schemas import ConformError
from app.store.mcp_client import (
    McpClickHouseReader,
    _parse_mcp_result,
    guard_sql,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_config(url: str = "http://localhost:8000", token: str = "") -> SimpleNamespace:
    return SimpleNamespace(clickhouse_mcp_url=url, clickhouse_mcp_auth_token=token)


def _jsonrpc_response(rows: list[dict]) -> str:
    """Build a valid MCP JSON-RPC 2.0 response wrapping *rows*."""
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [{"type": "text", "text": json.dumps(rows)}],
            },
        }
    )


def _mock_urlopen(body: str, status: int = 200):
    """Return a context-manager mock that mimics urllib.request.urlopen."""
    resp = BytesIO(body.encode())
    resp.status = status
    resp.read = resp.read  # already present on BytesIO
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=resp)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def _expect_conform_code(code: str, fn, *args, **kwargs):
    """Call *fn* and assert it raises ConformError with the expected *code*."""
    with pytest.raises(ConformError) as exc_info:
        fn(*args, **kwargs)
    assert exc_info.value.error.code == code


# ---------------------------------------------------------------------------
# guard_sql
# ---------------------------------------------------------------------------

class TestGuardSql:
    def test_select_passes(self) -> None:
        assert guard_sql("SELECT 1") == "SELECT 1 LIMIT 500"

    def test_with_cte_passes(self) -> None:
        sql = "WITH t AS (SELECT 1) SELECT * FROM t LIMIT 10"
        assert guard_sql(sql) == sql

    def test_trailing_semicolon_stripped(self) -> None:
        result = guard_sql("SELECT 1;")
        assert not result.endswith(";")

    def test_multi_statement_rejected(self) -> None:
        _expect_conform_code("SQL_MULTI_STATEMENT", guard_sql, "SELECT 1; DROP TABLE t")

    def test_insert_rejected(self) -> None:
        _expect_conform_code(
            "SQL_FORBIDDEN_KEYWORD",
            guard_sql,
            "SELECT 1 UNION ALL INSERT INTO t VALUES (1)",
        )

    def test_drop_rejected(self) -> None:
        _expect_conform_code("SQL_FORBIDDEN_KEYWORD", guard_sql, "SELECT drop FROM t LIMIT 5")

    def test_non_select_rejected(self) -> None:
        _expect_conform_code("SQL_NOT_SELECT", guard_sql, "INSERT INTO t VALUES (1)")

    def test_limit_not_doubled(self) -> None:
        sql = "SELECT * FROM t LIMIT 10"
        result = guard_sql(sql)
        assert result.lower().count("limit") == 1


# ---------------------------------------------------------------------------
# _parse_mcp_result
# ---------------------------------------------------------------------------

class TestParseMcpResult:
    def test_plain_json_rpc(self) -> None:
        rows = [{"x": 1}, {"x": 2}]
        assert _parse_mcp_result(_jsonrpc_response(rows)) == rows

    def test_sse_stream(self) -> None:
        rows = [{"col": "val"}]
        sse_body = f"event: message\ndata: {_jsonrpc_response(rows)}\n\n"
        assert _parse_mcp_result(sse_body) == rows

    def test_multiple_sse_frames_takes_last(self) -> None:
        early = [{"old": True}]
        final = [{"new": True}]
        body = (
            f"data: {_jsonrpc_response(early)}\n\n"
            f"data: {_jsonrpc_response(final)}\n\n"
        )
        assert _parse_mcp_result(body) == final

    def test_error_envelope(self) -> None:
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -1, "message": "boom"}})
        _expect_conform_code("MCP_ERROR", _parse_mcp_result, body)

    def test_empty_content_returns_empty(self) -> None:
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"content": []}})
        assert _parse_mcp_result(body) == []

    def test_data_key_unwrap(self) -> None:
        """When text payload is {data: [...]}, rows come from the 'data' key."""
        inner = {"data": [{"a": 1}]}
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"content": [{"type": "text", "text": json.dumps(inner)}]},
            }
        )
        assert _parse_mcp_result(body) == [{"a": 1}]


# ---------------------------------------------------------------------------
# McpClickHouseReader.run_select_query
# ---------------------------------------------------------------------------

class TestMcpClickHouseReader:
    @patch("app.store.mcp_client.urllib.request.urlopen")
    def test_happy_path(self, mock_urlopen: MagicMock) -> None:
        rows = [{"id": 1, "name": "alpha"}]
        mock_urlopen.return_value = _mock_urlopen(_jsonrpc_response(rows))

        reader = McpClickHouseReader(_fake_config())
        result = reader.run_select_query("SELECT * FROM t LIMIT 10")

        assert result == rows
        # Verify the JSON-RPC request was well-formed
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert req.full_url == "http://localhost:8000/mcp"
        sent = json.loads(req.data.decode())
        assert sent["method"] == "tools/call"
        assert sent["params"]["name"] == "run_query"
        assert reader.mode == "live_mcp"

    @patch("app.store.mcp_client.urllib.request.urlopen")
    def test_bearer_token_is_sent(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_urlopen(_jsonrpc_response([]))
        reader = McpClickHouseReader(_fake_config(token="test-token"))
        reader.run_select_query("SELECT 1 LIMIT 1")
        req = mock_urlopen.call_args[0][0]
        assert req.headers["Authorization"] == "Bearer test-token"

    @patch("app.store.mcp_client.urllib.request.urlopen")
    def test_params_substituted(self, mock_urlopen: MagicMock) -> None:
        rows: list[dict] = []
        mock_urlopen.return_value = _mock_urlopen(_jsonrpc_response(rows))

        reader = McpClickHouseReader(_fake_config())
        reader.run_select_query(
            "SELECT * FROM t WHERE name = {name:String} LIMIT 5",
            params={"name": "hello"},
        )

        req = mock_urlopen.call_args[0][0]
        sent = json.loads(req.data.decode())
        assert "'hello'" in sent["params"]["arguments"]["query"]

    @patch("app.store.mcp_client.urllib.request.urlopen")
    def test_unreachable_raises(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = OSError("Connection refused")
        reader = McpClickHouseReader(_fake_config())
        _expect_conform_code("MCP_UNREACHABLE", reader.run_select_query, "SELECT 1 LIMIT 1")

    @patch("app.store.mcp_client.urllib.request.urlopen")
    def test_mcp_error_response(self, mock_urlopen: MagicMock) -> None:
        error_body = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "Invalid Request"}}
        )
        mock_urlopen.return_value = _mock_urlopen(error_body)

        reader = McpClickHouseReader(_fake_config())
        _expect_conform_code("MCP_ERROR", reader.run_select_query, "SELECT 1 LIMIT 1")

    @patch("app.store.mcp_client.urllib.request.urlopen")
    def test_sse_response_parsed(self, mock_urlopen: MagicMock) -> None:
        rows = [{"metric": 42}]
        sse = f"event: message\ndata: {_jsonrpc_response(rows)}\n\n"
        mock_urlopen.return_value = _mock_urlopen(sse)

        reader = McpClickHouseReader(_fake_config())
        assert reader.run_select_query("SELECT metric FROM t LIMIT 1") == rows

    def test_trailing_slash_stripped(self) -> None:
        reader = McpClickHouseReader(_fake_config("http://localhost:8000/"))
        assert reader._url == "http://localhost:8000"

    def test_mode_label(self) -> None:
        reader = McpClickHouseReader(_fake_config())
        assert reader.mode == "configured_unverified"
