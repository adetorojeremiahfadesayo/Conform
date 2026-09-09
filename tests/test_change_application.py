"""Regression coverage for applying edits before cache lookup; deterministic tests."""
from __future__ import annotations

from app.core.changes import changed_graph
from app.domain.schemas import Change, ChangeIntent, ChangeKind


def test_edit_changes_descendant_fingerprints_without_mutating_base(diamond_graph):
    before = {nid: node.fingerprint for nid, node in diamond_graph.nodes.items()}
    intent = ChangeIntent(kind=ChangeKind.ASSET_EDIT, node_id="b", new_inputs={"prompt": "new"})
    target = changed_graph(Change(kind=intent.kind, intent=intent), diamond_graph)
    assert target.nodes["b"].inputs["prompt"] == "new"
    assert target.nodes["b"].fingerprint != before["b"]
    assert target.nodes["d"].fingerprint != before["d"]
    assert target.nodes["a"].fingerprint == before["a"]
    assert target.nodes["c"].fingerprint == before["c"]
    assert {nid: node.fingerprint for nid, node in diamond_graph.nodes.items()} == before
