"""Tests for the Tamper Switch (PRD §5 FR-7.4)."""

from __future__ import annotations

from app.agents.coordinator import Coordinator
from app.config import Config


def test_tamper_artifact_causes_verification_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFORM_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("CONFORM_EVENTS_DB", str(tmp_path / "events.db"))

    coord = Coordinator(Config())

    # Submit change, estimate, approve, and build
    change = coord.submit_change("edit node campaign_a.source: set prompt to new brief")
    coord.estimate_change(change.change_id)
    coord.approve(change.change_id, actor="test_runner")
    build_res = coord.build(change.change_id)

    release_id = build_res.release.release_id

    # 1. Initial verification must pass 100%
    initial_report = coord.verify(release_id)
    assert initial_report.ok is True
    assert all(a["ok"] for a in initial_report.per_artifact)

    # 2. Corrupt one byte of an artifact in the release
    target_node = build_res.release.artifacts[0].node_id
    tamper_res = coord.tamper_release_artifact(release_id, node_id=target_node)
    assert tamper_res.node_id == target_node

    # 3. Verification must now FAIL with byte mismatch
    tampered_report = coord.verify(release_id)
    assert tampered_report.ok is False
    tampered_art = next(a for a in tampered_report.per_artifact if a["node_id"] == target_node)
    assert tampered_art["ok"] is False

    # A visitor's tamper demonstration must not poison the shared generation cache.
    from app.core.verify import verify_release
    assert verify_release(release_id, build_res.release.artifacts, coord.store).ok
