"""Blast-radius / dirty-subtree resolution — deterministic core.

Given a change (rule change or asset edit), computes exactly which nodes are
dirty and which are reused, and produces the Estimate with cost, duration,
findings, and the graph hash the estimate is pinned to.
"""

from __future__ import annotations

from decimal import Decimal

from app.core.closure import ClosureRow, blast_radius
from app.core.cost import estimate_nodes
from app.core.fingerprint import hash_graph
from app.core.graph import PipelineGraph
from app.core.rules import dirty_nodes_for_rule, evaluate_rule
from app.domain.schemas import (
    Change,
    ChangeKind,
    ConformError,
    DirtyNode,
    DirtyReason,
    Estimate,
    Finding,
    RuleOp,
)


def resolve_dirty_sources(change: Change, graph: PipelineGraph) -> list[str]:
    """The directly-affected nodes for a change (depth 0 of the blast radius)."""
    intent = change.intent
    if intent.kind == ChangeKind.ASSET_EDIT:
        if not intent.node_id or intent.node_id not in graph.nodes:
            raise ConformError("UNKNOWN_NODE", f"asset edit targets unknown node: {intent.node_id}")
        return [intent.node_id]
    if intent.kind == ChangeKind.RULE_CHANGE:
        if intent.rule_op in (RuleOp.NEW, RuleOp.EDIT):
            if intent.rule is None:
                raise ConformError("MISSING_RULE", "rule change has no rule payload")
            return dirty_nodes_for_rule(intent.rule, graph)
        if intent.rule_op == RuleOp.REMOVE:
            # Removing a rule makes previously-flagged nodes clean again; the
            # engine re-evaluates the remaining ruleset elsewhere. Seed is the
            # nodes carrying the rule in their recipe.
            return sorted(
                nid
                for nid, node in graph.nodes.items()
                if intent.rule_id in (node.recipe.get("applied_rules") or [])
            )
    raise ConformError("UNSUPPORTED_CHANGE", f"cannot resolve change kind {intent.kind}")


def compute_estimate(
    change: Change,
    graph: PipelineGraph,
    closure: list[ClosureRow],
    budget_usd: Decimal,
) -> Estimate:
    """Full estimate: dirty set, reuse, cost, duration, findings, graph pin."""
    sources = resolve_dirty_sources(change, graph)
    dirty = blast_radius(closure, sources)
    dirty_ids = sorted(dirty)

    source_set = set(sources)
    rule_hit = change.intent.kind == ChangeKind.RULE_CHANGE
    dirty_nodes = [
        DirtyNode(
            node_id=nid,
            depth=depth,
            reason=(
                (DirtyReason.RULE_SCOPE_HIT if rule_hit else DirtyReason.NODE_SPEC_CHANGED)
                if nid in source_set
                else DirtyReason.UPSTREAM_FINGERPRINT_CHANGED
            ),
        )
        for nid, depth in dirty.items()
    ]
    reused_ids = sorted(nid for nid in graph.nodes if nid not in dirty)

    findings: list[Finding] = []
    if change.intent.kind == ChangeKind.RULE_CHANGE and change.intent.rule is not None:
        findings = evaluate_rule(change.intent.rule, graph, change.change_id)

    kinds = [graph.nodes[nid].kind for nid in dirty_ids]
    cost, seconds, breakdown = estimate_nodes(kinds)

    return Estimate(
        change_id=change.change_id,
        dirty_node_ids=dirty_ids,
        dirty_nodes=dirty_nodes,
        reused_node_ids=reused_ids,
        estimated_cost_usd=cost,
        estimated_seconds=round(seconds, 2),
        per_model=breakdown,
        findings=findings,
        graph_hash=hash_graph(list(graph.nodes.values())),
        budget_exceeded=cost > budget_usd,
    )
