"""Shared fixtures for the CONFORM test suite."""

from __future__ import annotations

import pytest

from app.core.graph import PipelineGraph
from app.domain.schemas import NodeKind, NodeSpec


@pytest.fixture(autouse=True)
def clean_test_env(monkeypatch):
    """Guarantees unit tests run in offline/stubbed mode unless explicitly marked."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "")
    monkeypatch.setenv("CLICKHOUSE_HOST", "")
    monkeypatch.setenv("ARTIFACT_BUCKET", "")
    monkeypatch.setenv("CLICKHOUSE_MCP_URL", "")
    monkeypatch.setenv("JUDGE_MODE", "false")


def make_node(
    node_id: str,
    kind: NodeKind,
    parents: list[str] | None = None,
    inputs: dict | None = None,
    recipe: dict | None = None,
    campaign_id: str = "campaign_a",
    territory: str = "master",
) -> NodeSpec:
    return NodeSpec(
        node_id=node_id,
        campaign_id=campaign_id,
        territory=territory,
        kind=kind,
        inputs=inputs or {"prompt": f"prompt for {node_id}"},
        recipe=recipe or {"model": "test-model", "seed": 1},
        parents=parents or [],
    )


@pytest.fixture
def diamond_specs() -> list[NodeSpec]:
    """a -> b, a -> c, b -> d, c -> d (classic diamond)."""
    return [
        make_node("a", NodeKind.SOURCE),
        make_node("b", NodeKind.SHOT_PLAN, parents=["a"]),
        make_node("c", NodeKind.KEYFRAME, parents=["a"]),
        make_node("d", NodeKind.PACKAGE, parents=["b", "c"]),
    ]


@pytest.fixture
def diamond_graph(diamond_specs) -> PipelineGraph:
    return PipelineGraph(diamond_specs)


@pytest.fixture
def fanout_specs() -> list[NodeSpec]:
    """One shared upstream (source -> shot_plan -> keyframe) fanning out to
    4 territories at the copy/package leaves — a scaled-down slate."""
    specs = [
        make_node("src", NodeKind.SOURCE),
        make_node("plan", NodeKind.SHOT_PLAN, parents=["src"]),
        make_node("key", NodeKind.KEYFRAME, parents=["plan"]),
    ]
    for terr in ["de", "fr", "jp", "br"]:
        specs.append(
            make_node(f"copy_{terr}", NodeKind.COPY, parents=["plan"], territory=terr)
        )
        specs.append(
            make_node(f"pkg_{terr}", NodeKind.PACKAGE, parents=["key", f"copy_{terr}"], territory=terr)
        )
    return specs


@pytest.fixture
def fanout_graph(fanout_specs) -> PipelineGraph:
    return PipelineGraph(fanout_specs)
