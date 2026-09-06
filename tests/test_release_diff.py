"""Tests for Release Diffing (PRD §5 FR-9.3, FR-10)."""

from __future__ import annotations

from decimal import Decimal

from app.agents.coordinator import Coordinator
from app.config import Config


def test_diff_two_releases(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFORM_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("CONFORM_EVENTS_DB", str(tmp_path / "events.db"))

    coord = Coordinator(Config())

    # Build 1: change source
    c1 = coord.submit_change("edit node campaign_a.source: set prompt to v1")
    coord.estimate_change(c1.change_id)
    coord.approve(c1.change_id, actor="tester")
    b1 = coord.build(c1.change_id)
    r1 = b1.release.release_id

    # Build 2: change keyframe
    c2 = coord.submit_change("edit node campaign_a.keyframe: set prompt to v2")
    coord.estimate_change(c2.change_id)
    coord.approve(c2.change_id, actor="tester")
    b2 = coord.build(c2.change_id)
    r2 = b2.release.release_id

    diff = coord.diff_releases(r1, r2)
    assert diff.release_a == r1
    assert diff.release_b == r2
    assert len(diff.nodes_removed) == 42
    assert "campaign_a.source" in diff.nodes_removed
    assert diff.cost_delta_usd != Decimal("0")
