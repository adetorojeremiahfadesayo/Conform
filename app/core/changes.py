"""Apply validated change contracts to an isolated graph; deterministic core."""
from __future__ import annotations

from app.core.dirty import resolve_dirty_sources
from app.core.graph import PipelineGraph
from app.domain.schemas import Change, ChangeKind, NodeSpec, RuleOp


def changed_graph(change: Change, graph: PipelineGraph) -> PipelineGraph:
    sources = set(resolve_dirty_sources(change, graph))
    specs = []
    for node in graph.nodes.values():
        spec = NodeSpec.model_validate(node.model_dump()).model_copy(deep=True)
        if node.node_id in sources:
            if change.intent.kind == ChangeKind.ASSET_EDIT:
                spec.inputs.update(change.intent.new_inputs or {})
            else:
                rules = dict(spec.recipe.get("project_rules", {}))
                rule_id = change.intent.rule_id
                if change.intent.rule_op == RuleOp.REMOVE:
                    rules.pop(rule_id, None)
                elif change.intent.rule:
                    rules[change.intent.rule.rule_id] = change.intent.rule.model_dump(mode="json")
                spec.recipe["project_rules"] = rules
        specs.append(spec)
    return PipelineGraph(specs)
