"""Tests for the Analyst Agent (PRD §5 FR-8.4, FR-8.5, FR-8.6)."""

from __future__ import annotations

import pytest

from app.agents.analyst import AnalystAgent
from app.config import Config
from app.domain.schemas import ConformError
from app.store.clickhouse_writer import SQLiteWriter
from app.store.mcp_client import DirectReader


@pytest.fixture
def analyst(tmp_path):
    config = Config()
    writer = SQLiteWriter(path=tmp_path / "test_events.db")
    reader = DirectReader(writer)
    return AnalystAgent(config, reader)


def test_analyst_natural_language_spend_by_model(analyst):
    res = analyst.ask(query="What is our spend by model?")
    assert "provider_calls" in res.sql
    assert "spend_usd" in res.sql
    assert "LIMIT" in res.sql
    assert res.interpretation_mode == "fallback_deterministic"
    assert res.reader_mode == "fallback_direct"
    assert isinstance(res.answer, str)


def test_analyst_natural_language_reuse(analyst):
    res = analyst.ask(query="How many nodes were reused from cache?")
    assert "node_runs" in res.sql
    assert "cache_hit" in res.sql
    assert isinstance(res.answer, str)


def test_analyst_natural_language_retries(analyst):
    res = analyst.ask(query="Which transient failures were retried?")
    assert "attempt" in res.sql
    assert "LIMIT" in res.sql


def test_analyst_direct_sql_execution(analyst):
    res = analyst.ask(sql="SELECT node_kind, count() FROM node_runs GROUP BY node_kind")
    assert "node_kind" in res.sql
    assert "LIMIT" in res.sql


def test_analyst_rejects_ddl_and_writes(analyst):
    with pytest.raises(ConformError) as exc:
        analyst.ask(sql="DROP TABLE node_runs")
    assert exc.value.error.code in ("SQL_NOT_SELECT", "SQL_FORBIDDEN_KEYWORD")

    with pytest.raises(ConformError) as exc2:
        analyst.ask(sql="INSERT INTO node_runs VALUES ('a')")
    assert exc2.value.error.code in ("SQL_NOT_SELECT", "SQL_FORBIDDEN_KEYWORD")

    with pytest.raises(ConformError) as exc3:
        analyst.ask(sql="SELECT * FROM node_runs WHERE 1=1; DROP TABLE node_runs")
    assert exc3.value.error.code in ("SQL_MULTI_STATEMENT", "SQL_FORBIDDEN_KEYWORD")
