"""Demo rule engine — deterministic core.

Evaluates declarative rule predicates against graph nodes. 100% deterministic;
no LLM ever touches a verdict. These are demo project rules — nothing here is
regulatory, legal, or advertising-standards review.

Predicate grammar (a small, closed spec):
  {"field": <dotted path into node inputs>, "op": <op>, "value": <any>}
ops: exists, not_exists, equals, not_equals, contains, not_contains,
     min_len (string length >= value), max_len (string length <= value)
A node *violates* a rule when the predicate evaluates true.
"""

from __future__ import annotations

from typing import Any

from app.core.graph import PipelineGraph
from app.domain.schemas import ConformError, Finding, Node, Rule


def _resolve_field(node: Node, dotted: str) -> Any:
    cur: Any = node.inputs
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _eval_predicate(node: Node, predicate: dict[str, Any]) -> bool:
    field = predicate.get("field", "")
    op = predicate.get("op", "")
    value = predicate.get("value")
    actual = _resolve_field(node, field) if field else None

    if op == "exists":
        return actual is not None
    if op == "not_exists":
        return actual is None
    if op == "equals":
        return actual == value
    if op == "not_equals":
        return actual is not None and actual != value
    if op == "contains":
        return isinstance(actual, str) and isinstance(value, str) and value in actual
    if op == "not_contains":
        return isinstance(actual, str) and isinstance(value, str) and value not in actual
    if op == "min_len":
        return isinstance(actual, str) and isinstance(value, int) and len(actual) >= value
    if op == "max_len":
        return isinstance(actual, str) and isinstance(value, int) and len(actual) > value
    if not op:
        return False
    raise ConformError("UNKNOWN_PREDICATE_OP", f"unknown predicate op: {op}")


def _in_scope(node: Node, rule: Rule) -> bool:
    if rule.node_kinds and node.kind not in rule.node_kinds:
        return False
    if rule.territories and node.territory not in rule.territories:
        return False
    return True


def evaluate_rule(rule: Rule, graph: PipelineGraph, change_id: str) -> list[Finding]:
    """Evaluate one rule over the whole graph. Returns findings sorted by node_id."""
    findings: list[Finding] = []
    for nid in sorted(graph.nodes):
        node = graph.nodes[nid]
        if not _in_scope(node, rule):
            continue
        if _eval_predicate(node, rule.predicate):
            findings.append(
                Finding(
                    change_id=change_id,
                    rule_id=rule.rule_id,
                    node_id=node.node_id,
                    territory=node.territory,
                    severity=rule.severity,
                    reason=f"{rule.name}: {rule.description or rule.predicate}",
                )
            )
    return findings


def dirty_nodes_for_rule(rule: Rule, graph: PipelineGraph) -> list[str]:
    """Node ids directly affected by a rule (the blast-radius seed set)."""
    return sorted(
        nid
        for nid, node in graph.nodes.items()
        if _in_scope(node, rule)
    )
