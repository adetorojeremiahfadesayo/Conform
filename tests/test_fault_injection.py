"""Tests for Dynamic Fault Injection (PRD §5 FR-6.5)."""

from __future__ import annotations

from app.agents.coordinator import Coordinator
from app.config import Config


def test_dynamic_fault_injection_toggle(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFORM_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("CONFORM_EVENTS_DB", str(tmp_path / "events.db"))

    coord = Coordinator(Config())

    assert coord.fault_injection_mode == "off"

    # Turn fault injection on
    coord.set_fault_injection("transient_once")
    assert coord.fault_injection_mode == "transient_once"
    assert coord.system_status()["fault_injection"] == "transient_once"

    # Build clip with transient timeout; build engine should auto-retry and succeed
    c = coord.submit_change("edit node campaign_a.clip: set prompt to new hero")
    coord.estimate_change(c.change_id)
    coord.approve(c.change_id, actor="tester")
    build_res = coord.build(c.change_id)

    # Must have recorded at least 1 retry on the clip node
    clip_runs = [r for r in build_res.runs if r.node_id == "campaign_a.clip"]
    assert len(clip_runs) >= 2
    assert any(r.status == "failed" and r.error_class.value == "transient" for r in clip_runs)
    assert any(r.status == "ok" and r.attempt >= 2 for r in clip_runs)
    assert build_res.retries >= 1
