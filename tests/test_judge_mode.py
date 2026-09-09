"""Public Judge Mode must be cached-only, read-only, and route constrained."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.agents.coordinator import Coordinator
from app.api.deps import reset_coordinator
from app.api.main import create_app
from app.config import Config
from app.domain.schemas import ConformError


def test_judge_mode_blocks_live_adk_when_cached_interpretation_is_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("JUDGE_MODE", "true")
    monkeypatch.setenv("CONFORM_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("CONFORM_EVENTS_DB", str(tmp_path / "events.db"))
    coord = Coordinator(Config())

    try:
        coord.execute_adk_preset("eu_disclaimer_2026")
    except ConformError as exc:
        assert exc.error.code == "JUDGE_CACHE_MISS"
    else:
        raise AssertionError("Judge Mode must never fall through to a live ADK call")


def test_judge_mode_rejects_custom_change_and_sql(monkeypatch):
    monkeypatch.setenv("JUDGE_MODE", "true")
    coord = Coordinator(Config())

    for action in (
        lambda: coord.submit_change("edit node campaign_a.source: set prompt to attacker text"),
        lambda: coord.ask(query="anything", sql="SELECT 1"),
    ):
        try:
            action()
        except ConformError as exc:
            assert exc.error.code == "JUDGE_ACTION_BLOCKED"
        else:
            raise AssertionError("Judge Mode accepted an arbitrary public action")


def test_judge_api_blocks_custom_change_route(monkeypatch):
    monkeypatch.setenv("JUDGE_MODE", "true")
    reset_coordinator()
    client = TestClient(create_app())
    response = client.post("/api/changes", json={"text": "untrusted"})
    assert response.status_code == 403
    assert response.json()["code"] == "JUDGE_ACTION_BLOCKED"
