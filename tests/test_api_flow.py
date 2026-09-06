"""End-to-end API flow: the full demo path over HTTP plus negative paths.

Covers the §8 invariants at the boundary: no build before approval, approval
gate, build + verification, and the guarded analyst path.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.deps import reset_coordinator
from app.api.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFORM_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("CONFORM_EVENTS_DB", str(tmp_path / "events.db"))
    reset_coordinator()
    return TestClient(create_app())


def test_system_status_truthful_labels(client):
    status = client.get("/api/system/status").json()
    assert status["vertex"] == "fallback_stub"
    assert status["clickhouse_read_mcp"] in ("fallback_direct", "live_mcp")
    assert status["nodes"] == 252  # 3 campaigns x (4 master + 40 copy + 40 package)


def test_campaigns_seeded(client):
    campaigns = client.get("/api/campaigns").json()
    assert len(campaigns) == 3
    assert all(len(c["territories"]) == 40 for c in campaigns)


def test_full_demo_flow_rule_change(client):
    # 1. submit the compliance-change trigger (V3 demo narrative)
    resp = client.post(
        "/api/changes",
        json={"text": "new rule R-DISC-004 on copy in territories de fr: field disclaimer min_len 40"},
    )
    assert resp.status_code == 201
    change = resp.json()
    change_id = change["change_id"]
    assert change["intent"]["interpretation_mode"] == "fallback_deterministic"

    # 2. estimate — blast radius before any spend
    est = client.post(f"/api/changes/{change_id}/estimate").json()
    # 2 copy nodes directly in scope, each + its package = 4 dirty of 252
    assert set(est["dirty_node_ids"]) == {
        "campaign_a.copy.de", "campaign_a.copy.fr",
        "campaign_b.copy.de", "campaign_b.copy.fr",
        "campaign_c.copy.de", "campaign_c.copy.fr",
        "campaign_a.package.de", "campaign_a.package.fr",
        "campaign_b.package.de", "campaign_b.package.fr",
        "campaign_c.package.de", "campaign_c.package.fr",
    }
    assert len(est["reused_node_ids"]) == 252 - 12

    # 3. build before approval must be refused — the gate
    refused = client.post(f"/api/changes/{change_id}/build")
    assert refused.status_code == 409
    assert refused.json()["code"] == "NOT_APPROVED"

    # 4. approve, then build
    approval = client.post(f"/api/changes/{change_id}/approve", json={"actor": "producer (simulated)"})
    assert approval.status_code == 200
    assert approval.json()["actor_is_simulated"] is True

    built = client.post(f"/api/changes/{change_id}/build").json()
    assert built["nodes_rebuilt"] == 12
    assert built["release"]["release_id"] == "release_001"
    assert len(built["runs"]) == 12

    # 5. verify the release
    report = client.get("/api/releases/release_001/verify").json()
    assert report["ok"] is True
    assert len(report["per_artifact"]) == 12


def test_asset_edit_flow(client):
    resp = client.post("/api/changes", json={"text": "edit node campaign_a.clip: set prompt to reshoot hero"})
    change_id = resp.json()["change_id"]
    est = client.post(f"/api/changes/{change_id}/estimate").json()
    # clip dirties all 40 packages of campaign_a; copies are untouched
    assert "campaign_a.clip" in est["dirty_node_ids"]
    assert len(est["dirty_node_ids"]) == 41
    assert "campaign_b.clip" in est["reused_node_ids"]


def test_reject_blocks_build(client):
    resp = client.post("/api/changes", json={"text": "edit node campaign_a.clip: set prompt to x"})
    change_id = resp.json()["change_id"]
    client.post(f"/api/changes/{change_id}/estimate")
    client.post(f"/api/changes/{change_id}/reject", json={"actor": "legal (simulated)"})
    refused = client.post(f"/api/changes/{change_id}/approve", json={})
    assert refused.status_code == 409


def test_unknown_change_404(client):
    assert client.post("/api/changes/nope/estimate").status_code == 404
    assert client.post("/api/changes/nope/approve", json={}).status_code == 404
    assert client.get("/api/releases/nope/verify").status_code == 404


def test_unparseable_change_is_explicit_error(client):
    resp = client.post("/api/changes", json={"text": "make it pop"})
    assert resp.status_code == 422
    assert resp.json()["code"] == "PARSE_FAILED"


def test_analyst_sql_guard(client):
    # write attempt refused
    bad = client.post("/api/analytics/ask", json={"sql": "DROP TABLE node_runs"})
    assert bad.status_code == 422
    # multi-statement refused
    bad2 = client.post("/api/analytics/ask", json={"sql": "SELECT 1; SELECT 2"})
    assert bad2.status_code == 422
    # plain select works and auto-LIMITs
    ok = client.post("/api/analytics/ask", json={"sql": "SELECT node_kind, count() FROM node_runs GROUP BY node_kind"})
    assert ok.status_code == 200
    assert "LIMIT" in ok.json()["sql"].upper()


def test_analyst_reads_what_builds_wrote(client):
    resp = client.post("/api/changes", json={"text": "edit node campaign_a.clip: set prompt to new hero"})
    change_id = resp.json()["change_id"]
    client.post(f"/api/changes/{change_id}/estimate")
    client.post(f"/api/changes/{change_id}/approve", json={})
    client.post(f"/api/changes/{change_id}/build")
    rows = client.post(
        "/api/analytics/ask",
        json={"sql": "SELECT count() AS n FROM node_runs WHERE is_seeded = 0"},
    ).json()["rows"]
    assert rows[0]["n"] == 41


def test_audit_records_flow(client):
    resp = client.post("/api/changes", json={"text": "edit node campaign_a.clip: set prompt to v2"})
    change_id = resp.json()["change_id"]
    client.post(f"/api/changes/{change_id}/estimate")
    client.post(f"/api/changes/{change_id}/approve", json={"actor": "producer (simulated)"})
    client.post(f"/api/changes/{change_id}/build")
    events = [e["event"] for e in client.get("/api/audit").json()]
    assert events == ["change_interpreted", "estimate_ready", "approved", "build_complete"]
