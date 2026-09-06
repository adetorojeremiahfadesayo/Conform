"""Blast radius, dirty resolution, and estimate correctness (FR-3, FR-4)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.closure import blast_radius, compute_closure
from app.core.dirty import compute_estimate, resolve_dirty_sources
from app.domain.schemas import (
    Change,
    ChangeIntent,
    ChangeKind,
    ConformError,
    NodeKind,
    Rule,
    RuleOp,
    Severity,
)


def _change(intent: ChangeIntent) -> Change:
    return Change(kind=intent.kind, intent=intent)


def test_closure_and_blast_radius_diamond(diamond_graph):
    closure = compute_closure(diamond_graph)
    dirty = blast_radius(closure, ["a"])
    assert set(dirty) == {"a", "b", "c", "d"}
    assert dirty["a"] == 0
    assert dirty["d"] == 2  # shortest path a->b->d or a->c->d


def test_blast_radius_leaf_edit(diamond_graph):
    closure = compute_closure(diamond_graph)
    dirty = blast_radius(closure, ["c"])
    assert set(dirty) == {"c", "d"}


def test_fanout_blast_radius_single_territory(fanout_graph):
    closure = compute_closure(fanout_graph)
    dirty = blast_radius(closure, ["copy_de"])
    assert set(dirty) == {"copy_de", "pkg_de"}


def test_fanout_blast_radius_shared_upstream(fanout_graph):
    closure = compute_closure(fanout_graph)
    dirty = blast_radius(closure, ["plan"])
    assert set(dirty) == {
        "plan",
        "key",
        "copy_de", "copy_fr", "copy_jp", "copy_br",
        "pkg_de", "pkg_fr", "pkg_jp", "pkg_br",
    }


def _rule(kinds, territories, predicate, rule_id="R-TEST-001"):
    return Rule(
        rule_id=rule_id,
        name="test rule",
        node_kinds=kinds,
        territories=territories,
        predicate=predicate,
        severity=Severity.WARNING,
    )


def test_rule_change_seeds_scoped_nodes(fanout_graph):
    rule = _rule([NodeKind.COPY], ["de", "fr"], {"field": "text", "op": "not_contains", "value": "⚠"})
    change = _change(ChangeIntent(kind=ChangeKind.RULE_CHANGE, rule_op=RuleOp.NEW, rule=rule))
    sources = resolve_dirty_sources(change, fanout_graph)
    assert sources == ["copy_de", "copy_fr"]


def test_rule_change_estimate_counts(fanout_graph):
    """New rule on copy in de+fr -> dirty = 2 copy + 2 packages; the other
    7 nodes (incl. the shared keyframe) are reused."""
    rule = _rule([NodeKind.COPY], ["de", "fr"], {"field": "prompt", "op": "not_contains", "value": "⚠"})
    change = _change(ChangeIntent(kind=ChangeKind.RULE_CHANGE, rule_op=RuleOp.NEW, rule=rule))
    closure = compute_closure(fanout_graph)
    est = compute_estimate(change, fanout_graph, closure, Decimal("5.00"))
    assert set(est.dirty_node_ids) == {"copy_de", "copy_fr", "pkg_de", "pkg_fr"}
    assert len(est.reused_node_ids) == 7
    assert est.estimated_cost_usd == Decimal("0.001")  # 2 copy @0.0005 + 2 package @0
    assert len(est.findings) == 2  # both scoped copy nodes violate (no ⚠ in prompt)
    assert not est.budget_exceeded


def test_asset_edit_estimate(fanout_graph):
    intent = ChangeIntent(kind=ChangeKind.ASSET_EDIT, node_id="key", new_inputs={"prompt": "new"})
    change = _change(intent)
    closure = compute_closure(fanout_graph)
    est = compute_estimate(change, fanout_graph, closure, Decimal("5.00"))
    assert set(est.dirty_node_ids) == {"key", "pkg_de", "pkg_fr", "pkg_jp", "pkg_br"}
    assert len(est.findings) == 0


def test_asset_edit_unknown_node_raises(fanout_graph):
    intent = ChangeIntent(kind=ChangeKind.ASSET_EDIT, node_id="ghost", new_inputs={})
    change = _change(intent)
    with pytest.raises(ConformError) as exc:
        resolve_dirty_sources(change, fanout_graph)
    assert exc.value.error.code == "UNKNOWN_NODE"


def test_budget_exceeded_flag(fanout_graph):
    intent = ChangeIntent(kind=ChangeKind.ASSET_EDIT, node_id="key", new_inputs={"prompt": "x"})
    change = _change(intent)
    closure = compute_closure(fanout_graph)
    est = compute_estimate(change, fanout_graph, closure, Decimal("0.001"))
    assert est.budget_exceeded


def test_dirty_reason_codes(fanout_graph):
    """A rebuild is never unexplained: source nodes carry the direct reason,
    downstream nodes carry UPSTREAM_FINGERPRINT_CHANGED."""
    from app.domain.schemas import DirtyReason

    intent = ChangeIntent(kind=ChangeKind.ASSET_EDIT, node_id="copy_de", new_inputs={"prompt": "x"})
    change = _change(intent)
    closure = compute_closure(fanout_graph)
    est = compute_estimate(change, fanout_graph, closure, Decimal("5.00"))
    reasons = {d.node_id: d.reason for d in est.dirty_nodes}
    assert reasons["copy_de"] == DirtyReason.NODE_SPEC_CHANGED
    assert reasons["pkg_de"] == DirtyReason.UPSTREAM_FINGERPRINT_CHANGED

    rule = _rule([NodeKind.COPY], ["fr"], {"field": "prompt", "op": "not_contains", "value": "⚠"})
    rule_change = _change(ChangeIntent(kind=ChangeKind.RULE_CHANGE, rule_op=RuleOp.NEW, rule=rule))
    est2 = compute_estimate(rule_change, fanout_graph, closure, Decimal("5.00"))
    reasons2 = {d.node_id: d.reason for d in est2.dirty_nodes}
    assert reasons2["copy_fr"] == DirtyReason.RULE_SCOPE_HIT
    assert reasons2["pkg_fr"] == DirtyReason.UPSTREAM_FINGERPRINT_CHANGED
