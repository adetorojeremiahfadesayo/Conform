"""Event store write path — ClickHouse Cloud when configured, SQLite otherwise.

Writes go through clickhouse-connect (the driver), never through the MCP
server — mcp-clickhouse is read-only by default and stays that way. The SQLite
fallback mirrors the same tables and is labelled `mode="fallback_sqlite"` in
system status so fallback persistence is never disguised as ClickHouse Cloud.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Protocol

from app.config import Config
from app.domain.schemas import ArtifactRecord, NodeRunRecord, ProviderCallRecord


class EventWriter(Protocol):
    mode: str

    def write_run(self, run: NodeRunRecord) -> None: ...
    def write_provider_call(self, call: ProviderCallRecord) -> None: ...
    def write_artifact(self, artifact: ArtifactRecord) -> None: ...
    def query(self, sql: str, params: dict | None = None) -> list[dict]: ...


_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS node_runs (
    tenant TEXT, campaign_id TEXT, territory TEXT, build_id TEXT, run_id TEXT,
    parent_run_id TEXT, node_id TEXT, node_kind TEXT, fingerprint TEXT,
    inputs_hash TEXT, recipe_hash TEXT, status TEXT, cache_hit INTEGER,
    attempt INTEGER, error_class TEXT, is_seeded INTEGER,
    started_at TEXT, ended_at TEXT, duration_ms INTEGER, cost_usd TEXT, bytes_out INTEGER
);
CREATE TABLE IF NOT EXISTS provider_calls (
    run_id TEXT, build_id TEXT, model TEXT, modality TEXT, region TEXT,
    latency_ms INTEGER, input_tokens INTEGER, output_tokens INTEGER,
    media_seconds REAL, cost_usd TEXT, http_status INTEGER, retryable INTEGER,
    is_seeded INTEGER, called_at TEXT
);
CREATE TABLE IF NOT EXISTS artifacts (
    fingerprint TEXT, build_id TEXT, node_id TEXT, uri TEXT, sha256 TEXT,
    bytes INTEGER, content_type TEXT, verify_ok INTEGER, verified_at TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS rule_findings (
    change_id TEXT, rule_id TEXT, node_id TEXT, territory TEXT,
    severity TEXT, reason TEXT, detected_at TEXT
);
CREATE TABLE IF NOT EXISTS graph_closure (
    campaign_id TEXT, build_id TEXT, ancestor TEXT, descendant TEXT, depth INTEGER
);
CREATE VIEW IF NOT EXISTS build_savings_mv AS
SELECT campaign_id,
       build_id,
       SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END) AS nodes_reused,
       SUM(CASE WHEN cache_hit = 0 THEN 1 ELSE 0 END) AS nodes_rebuilt,
       SUM(CASE WHEN cache_hit = 0 THEN CAST(cost_usd AS REAL) ELSE 0 END) AS spend_usd,
       SUM(CASE WHEN cache_hit = 1 THEN CAST(cost_usd AS REAL) ELSE 0 END) AS avoided_usd
FROM node_runs
GROUP BY campaign_id, build_id;
"""


class SQLiteWriter:
    """Local fallback. Same logical tables; mode label is honest.

    Thread safety: SQLite connections are bound to their creating thread.
    Uvicorn serves requests on worker threads, so a single shared connection
    used across them can fault at the C level (observed as exit 0xC0000005
    under load). All writes are therefore funnelled through a dedicated
    single-thread executor that owns the write connection for its whole life;
    reads use short-lived connections (WAL mode keeps them non-blocking).
    """

    mode = "fallback_sqlite"

    def __init__(self, path: Path | None = None):
        import os
        from concurrent.futures import ThreadPoolExecutor

        env_path = os.environ.get("CONFORM_EVENTS_DB", "").strip()
        self._path = path or (Path(env_path) if env_path else Path("output/conform_events.db"))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # One thread owns the write connection for its entire lifetime.
        self._writer_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="conform-sqlite")
        init = self._writer_pool.submit(self._open_write_conn)
        self._conn = init.result()  # created on the writer thread
        self._writer_pool.submit(self._init_schema).result()

    def _open_write_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        self._conn.executescript(_SQLITE_SCHEMA)
        self._conn.commit()

    def _insert(self, table: str, d: dict) -> None:
        cols = ", ".join(d)
        sql = f"INSERT INTO {table} ({cols}) VALUES ({', '.join('?' * len(d))})"
        self._writer_pool.submit(self._do_insert, sql, list(d.values())).result()

    def _do_insert(self, sql: str, values: list) -> None:
        self._conn.execute(sql, values)
        self._conn.commit()

    def write_run(self, run: NodeRunRecord) -> None:
        d = run.model_dump(mode="json")
        d["cost_usd"] = str(run.cost_usd)
        d["cache_hit"] = int(run.cache_hit)
        d["is_seeded"] = int(run.is_seeded)
        d["node_kind"] = run.node_kind.value
        d["error_class"] = run.error_class.value
        self._insert("node_runs", d)

    def write_provider_call(self, call: ProviderCallRecord) -> None:
        d = call.model_dump(mode="json")
        d["cost_usd"] = str(call.cost_usd)
        d["retryable"] = int(call.retryable)
        d["is_seeded"] = int(call.is_seeded)
        self._insert("provider_calls", d)

    def write_artifact(self, artifact: ArtifactRecord) -> None:
        d = artifact.model_dump(mode="json")
        d["verify_ok"] = None if artifact.verify_ok is None else int(artifact.verify_ok)
        self._insert("artifacts", d)

    def query(self, sql: str, params: dict | None = None) -> list[dict]:
        # Short-lived read connection; safe on any thread, non-blocking under WAL.
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute(sql, params or {})
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()


class ClickHouseWriter:
    """Live write path via clickhouse-connect. Import is lazy so the app runs
    without the driver installed in fallback mode."""

    mode = "live"

    def __init__(self, config: Config):
        try:
            import clickhouse_connect
        except ImportError as exc:
            raise RuntimeError("clickhouse-connect not installed") from exc
        self._client = clickhouse_connect.get_client(
            host=config.clickhouse_host,
            port=config.clickhouse_port,
            username=config.clickhouse_user,
            password=config.clickhouse_password,
            database=config.clickhouse_database,
            secure=True,
        )
        self._init_schema()

    def _init_schema(self) -> None:
        from pathlib import Path

        schema_file = Path(__file__).parent / "schema.sql"
        if schema_file.exists():
            statements = [s.strip() for s in schema_file.read_text(encoding="utf-8").split(";") if s.strip()]
            for stmt in statements:
                try:
                    self._client.command(stmt)
                except Exception:
                    pass

    def write_run(self, run: NodeRunRecord) -> None:
        self.write_runs([run])

    def write_runs(self, runs: list[NodeRunRecord]) -> None:
        if not runs:
            return
        rows = []
        cols = None
        for run in runs:
            d = run.model_dump(mode="json")
            d["node_kind"] = run.node_kind.value
            d["error_class"] = run.error_class.value
            d["cost_usd"] = str(run.cost_usd)
            if cols is None:
                cols = list(d)
            rows.append(list(d.values()))
        self._client.insert("node_runs", rows, column_names=cols)

    def write_provider_call(self, call: ProviderCallRecord) -> None:
        self.write_provider_calls([call])

    def write_provider_calls(self, calls: list[ProviderCallRecord]) -> None:
        if not calls:
            return
        rows = []
        cols = None
        for call in calls:
            d = call.model_dump(mode="json")
            d["cost_usd"] = str(call.cost_usd)
            if cols is None:
                cols = list(d)
            rows.append(list(d.values()))
        self._client.insert("provider_calls", rows, column_names=cols)

    def write_artifact(self, artifact: ArtifactRecord) -> None:
        d = artifact.model_dump(mode="json")
        self._client.insert("artifacts", [list(d.values())], column_names=list(d))

    def query(self, sql: str, params: dict | None = None) -> list[dict]:
        result = self._client.query(sql, parameters=params or {})
        return [dict(zip(result.column_names, row)) for row in result.result_rows]


def build_writer(config: Config) -> EventWriter:
    if config.clickhouse_live:
        return ClickHouseWriter(config)
    return SQLiteWriter()
