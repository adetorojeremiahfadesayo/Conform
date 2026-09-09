"""Tests for app.agents.adk_coordinator — Google ADK Agent integration."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.agents.adk_coordinator import AdkPipelineOrchestrator
from app.agents.coordinator import PRESET_DEFINITIONS, Coordinator, _preset_cache_key
from app.api.main import create_app
from app.config import Config
from app.domain.schemas import CachedAdkPreset


def _test_coordinator() -> Coordinator:
    cfg = Config(
        google_cloud_project="",  # offline fallback for tests
        clickhouse_host="",  # SQLite fallback
        artifact_bucket="",   # local filesystem
    )
    return Coordinator(cfg)


def test_adk_initialization():
    coord = _test_coordinator()
    assert hasattr(coord, "adk")
    assert isinstance(coord.adk, AdkPipelineOrchestrator)
    assert coord.adk.adk_agent.name == "conform_pipeline_compiler"
    assert len(coord.adk.tools) == 6

    # Verify status report
    status = coord.system_status()
    assert status.get("adk_agent") == "google_adk_2.8.0"


def test_adk_tool_definitions():
    coord = _test_coordinator()
    tool_names = [t.__name__ for t in coord.adk.tools]
    expected = [
        "interpret_and_estimate",
        "approve_spend",
        "build_dirty_subtree",
        "verify_release",
        "query_slate_history",
        "tamper_artifact",
    ]
    assert sorted(tool_names) == sorted(expected)

    # Every tool must have docstrings and valid type hints for ADK schema generation
    for tool in coord.adk.tools:
        assert tool.__doc__ is not None and len(tool.__doc__.strip()) > 10
        assert hasattr(tool, "__annotations__")


def test_adk_interpret_and_estimate_tool():
    coord = _test_coordinator()
    tool = coord.adk.tool_map["interpret_and_estimate"]
    res = tool("new rule R-DISC-004 on copy in territories de fr: field disclaimer min_len 40")

    assert res["status"] == "success"
    assert res["dirty_count"] == 12
    assert res["reused_count"] == 240
    assert res["total_assets"] == 252
    assert res["approval_required"] is True
    assert float(res["estimated_cost_usd"]) > 0


def test_adk_multi_step_goal_halts_at_approval_gate():
    coord = _test_coordinator()
    goal = "new rule R-DISC-004 on copy in territories de fr: field disclaimer min_len 40"
    result = coord.execute_adk_goal(goal, auto_approve=False)

    assert result.tools_called == ["interpret_and_estimate"]
    assert len(result.steps) == 1
    assert "Approval Gate" in result.final_answer
    assert result.change_id is not None
    assert result.release_id is None


def test_adk_multi_step_goal_full_autonomous_workflow():
    coord = _test_coordinator()
    goal = "new rule R-DISC-004 on copy in territories de fr: field disclaimer min_len 40"
    result = coord.execute_adk_goal(goal, auto_approve=True)

    expected_tools = ["interpret_and_estimate", "approve_spend", "build_dirty_subtree", "verify_release"]
    assert result.tools_called == expected_tools
    assert len(result.steps) == 4
    assert result.change_id is not None
    assert result.release_id is not None
    assert "Release" in result.final_answer
    assert "verified byte-exact" in result.final_answer


def test_adk_query_slate_history_tool():
    coord = _test_coordinator()
    tool = coord.adk.tool_map["query_slate_history"]
    res = tool("SELECT count() AS total FROM node_runs")

    assert res["status"] == "success"
    assert res["row_count"] >= 1


def test_adk_api_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("CONFORM_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("CONFORM_EVENTS_DB", str(tmp_path / "events.db"))
    from app.api.deps import reset_coordinator

    reset_coordinator()
    app = create_app()
    client = TestClient(app)

    resp = client.post(
        "/api/agents/adk/execute",
        json={
            "goal": "new rule R-DISC-004 on copy in territories de fr: field disclaimer min_len 40",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "google_adk_deterministic"
    assert data["tools_called"] == ["interpret_and_estimate"]
    assert "Approval Gate" in data["final_answer"]
    change_id = data["change_id"]

    preset_resp = client.post("/api/agents/adk/presets/eu_disclaimer_2026/execute")
    assert preset_resp.status_code == 200
    preset_data = preset_resp.json()
    assert preset_data["tools_called"] == ["interpret_and_estimate"]
    assert preset_data["change_id"] is not None
    preset_change = client.get(f"/api/changes/{preset_data['change_id']}").json()
    assert preset_change["preset_id"] == "eu_disclaimer_2026"

    missing_preset = client.post("/api/agents/adk/presets/missing/execute")
    assert missing_preset.status_code == 404
    assert missing_preset.json()["code"] == "UNKNOWN_PRESET"

    # Invariant: Resuming before human approval MUST fail with 409 NOT_APPROVED
    fail_resume = client.post("/api/agents/adk/resume", json={"change_id": change_id})
    assert fail_resume.status_code == 409
    assert fail_resume.json()["code"] == "NOT_APPROVED"

    # Human grants explicit approval
    appr_resp = client.post(f"/api/changes/{change_id}/approve", json={"actor": "producer"})
    assert appr_resp.status_code == 200

    # Resume ADK workflow
    resume_resp = client.post("/api/agents/adk/resume", json={"change_id": change_id})
    assert resume_resp.status_code == 200
    res_data = resume_resp.json()
    assert res_data["tools_called"] == ["build_dirty_subtree", "verify_release"]
    assert res_data["release_id"] is not None
    assert "verified byte-exact" in res_data["final_answer"]


def test_preset_api_endpoints(monkeypatch, tmp_path):
    monkeypatch.setenv("CONFORM_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("CONFORM_EVENTS_DB", str(tmp_path / "events.db"))
    from app.api.deps import reset_coordinator

    reset_coordinator()
    app = create_app()
    client = TestClient(app)

    # 1. GET /api/presets
    p_resp = client.get("/api/presets")
    assert p_resp.status_code == 200
    presets = p_resp.json()
    assert len(presets) >= 3
    assert any(p["preset_id"] == "eu_disclaimer_2026" for p in presets)

    # 2. POST /api/presets/eu_disclaimer_2026/changes
    submit_resp = client.post("/api/presets/eu_disclaimer_2026/changes")
    assert submit_resp.status_code == 201
    ch_data = submit_resp.json()
    assert ch_data["preset_id"] == "eu_disclaimer_2026"
    assert ch_data["change_id"] is not None

    # 3. GET /api/changes/{change_id}
    get_resp = client.get(f"/api/changes/{ch_data['change_id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["change_id"] == ch_data["change_id"]

    # 4. Unknown preset returns 404
    bad_resp = client.post("/api/presets/non_existent/changes")
    assert bad_resp.status_code == 404


def test_preset_replays_only_stored_live_interpretation(tmp_path):
    cfg = Config(
        google_cloud_project="",
        clickhouse_host="",
        artifact_bucket="",
        artifact_dir=str(tmp_path / "artifacts"),
        events_db=str(tmp_path / "events.db"),
    )
    coord = Coordinator(cfg)
    preset_id = "eu_disclaimer_2026"
    raw_text = PRESET_DEFINITIONS[preset_id]["raw_text"]
    source_change = coord.submit_preset(preset_id)
    source_change.intent.interpretation_mode = "gemini"
    cache_key = _preset_cache_key(preset_id, raw_text, cfg.vertex_text_model)
    snapshot = CachedAdkPreset(
        preset_id=preset_id,
        cache_key=cache_key,
        model_id=cfg.vertex_text_model,
        source_mode="google_adk_live",
        intent=source_change.intent,
    )
    coord.store.put(cache_key, snapshot.model_dump_json().encode("utf-8"), "application/json")

    result = coord.execute_adk_preset(preset_id)

    assert result.mode == "google_adk_cached_live_result"
    assert result.tools_called == []
    assert result.change_id in coord.changes
    assert result.change_id in coord.estimates
    assert coord.changes[result.change_id].intent.interpretation_mode == "gemini"
    assert any(entry["event"] == "adk_preset_cache_hit" for entry in coord.audit.entries)
