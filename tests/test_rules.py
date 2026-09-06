"""Rule engine predicate coverage (FR-3)."""

from __future__ import annotations

import pytest

from app.core.graph import PipelineGraph
from app.core.rules import evaluate_rule
from app.domain.schemas import ConformError, NodeKind, Rule, Severity
from tests.conftest import make_node


def _graph_with(text: str) -> PipelineGraph:
    return PipelineGraph([make_node("c1", NodeKind.COPY, inputs={"text": text})])


def _rule(op: str, value=None, field: str = "text") -> Rule:
    return Rule(
        rule_id="R-X",
        name="r",
        node_kinds=[NodeKind.COPY],
        predicate={"field": field, "op": op, "value": value},
        severity=Severity.WARNING,
    )


@pytest.mark.parametrize(
    "op,value,text,expect_finding",
    [
        ("contains", "legal", "see legal notice", True),
        ("contains", "legal", "nothing here", False),
        ("not_contains", "legal", "nothing here", True),
        ("equals", "x", "x", True),
        ("not_equals", "x", "y", True),
        ("min_len", 5, "hello", True),
        ("max_len", 3, "hello", True),
        ("exists", None, "hello", True),
        ("not_exists", None, "hello", False),
    ],
)
def test_predicate_ops(op, value, text, expect_finding):
    findings = evaluate_rule(_rule(op, value), _graph_with(text), "change_x")
    assert (len(findings) == 1) == expect_finding


def test_missing_field():
    findings = evaluate_rule(_rule("exists", field="ghost"), _graph_with("hi"), "change_x")
    assert findings == []
    findings = evaluate_rule(_rule("not_exists", field="ghost"), _graph_with("hi"), "change_x")
    assert len(findings) == 1


def test_unknown_op_raises():
    with pytest.raises(ConformError) as exc:
        evaluate_rule(_rule("explode"), _graph_with("hi"), "change_x")
    assert exc.value.error.code == "UNKNOWN_PREDICATE_OP"


def test_findings_carry_evidence():
    findings = evaluate_rule(_rule("not_contains", "legal"), _graph_with("no notice"), "change_x")
    f = findings[0]
    assert f.rule_id == "R-X" and f.node_id == "c1" and f.change_id == "change_x"
    assert f.territory == "master" and f.severity == Severity.WARNING
