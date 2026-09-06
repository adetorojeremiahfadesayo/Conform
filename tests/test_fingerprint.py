"""Fingerprint stability and propagation invariants (FR-2)."""

from __future__ import annotations

from app.core.fingerprint import fingerprint_node, hash_graph
from app.domain.schemas import NodeKind, NodeSpec
from tests.conftest import make_node


def test_same_spec_same_fingerprint():
    spec = make_node("n1", NodeKind.COPY, inputs={"a": 1, "b": [1, 2]})
    reordered = NodeSpec(
        node_id="n1",
        campaign_id="campaign_a",
        territory="master",
        kind=NodeKind.COPY,
        inputs={"b": [1, 2], "a": 1},  # key order differs — must not matter
        recipe={"model": "test-model", "seed": 1},
        parents=[],
    )
    assert fingerprint_node(spec, {}) == fingerprint_node(reordered, {})


def test_fingerprint_shape():
    fp = fingerprint_node(make_node("n1", NodeKind.COPY), {})
    assert len(fp) == 64
    assert fp == fp.lower()
    int(fp, 16)  # valid hex


def test_input_change_changes_fingerprint():
    base = fingerprint_node(make_node("n1", NodeKind.COPY, inputs={"text": "hello"}), {})
    changed = fingerprint_node(make_node("n1", NodeKind.COPY, inputs={"text": "hellp"}), {})
    assert base != changed


def test_recipe_change_changes_fingerprint():
    base = fingerprint_node(make_node("n1", NodeKind.CLIP, recipe={"model": "v1"}), {})
    changed = fingerprint_node(make_node("n1", NodeKind.CLIP, recipe={"model": "v2"}), {})
    assert base != changed


def test_parent_fingerprint_propagates(diamond_specs):
    """Changing a leaf input must change its own fingerprint; a parent built
    against the old child must differ from one built against the new."""
    from app.core.graph import PipelineGraph

    g1 = PipelineGraph(diamond_specs)
    modified = [
        s if s.node_id != "c" else make_node("c", NodeKind.KEYFRAME, parents=["a"], inputs={"prompt": "different"})
        for s in diamond_specs
    ]
    g2 = PipelineGraph(modified)
    assert g1.nodes["c"].fingerprint != g2.nodes["c"].fingerprint
    assert g1.nodes["d"].fingerprint != g2.nodes["d"].fingerprint  # transitive
    assert g1.nodes["b"].fingerprint == g2.nodes["b"].fingerprint  # unaffected sibling
    assert g1.nodes["a"].fingerprint == g2.nodes["a"].fingerprint  # unaffected ancestor


def test_graph_hash_order_independent(diamond_specs):
    from app.core.graph import PipelineGraph

    g1 = PipelineGraph(diamond_specs)
    g2 = PipelineGraph(list(reversed(diamond_specs)))
    assert hash_graph(list(g1.nodes.values())) == hash_graph(list(g2.nodes.values()))
