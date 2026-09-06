"""Graph invariants: cycle rejection, descendants, fan-out sharing (FR-1)."""

from __future__ import annotations

import pytest

from app.core.graph import PipelineGraph
from app.domain.schemas import ConformError, NodeKind
from tests.conftest import make_node


def test_cycle_rejected():
    specs = [
        make_node("a", NodeKind.SOURCE, parents=["c"]),
        make_node("b", NodeKind.COPY, parents=["a"]),
        make_node("c", NodeKind.PACKAGE, parents=["b"]),
    ]
    with pytest.raises(ConformError) as exc:
        PipelineGraph(specs)
    assert exc.value.error.code == "CYCLE_DETECTED"
    assert set(exc.value.error.detail["nodes_in_cycle"]) == {"a", "b", "c"}


def test_duplicate_node_rejected():
    specs = [make_node("a", NodeKind.SOURCE), make_node("a", NodeKind.SOURCE)]
    with pytest.raises(ConformError) as exc:
        PipelineGraph(specs)
    assert exc.value.error.code == "DUPLICATE_NODE"


def test_unknown_parent_rejected():
    specs = [make_node("a", NodeKind.COPY, parents=["ghost"])]
    with pytest.raises(ConformError) as exc:
        PipelineGraph(specs)
    assert exc.value.error.code == "UNKNOWN_PARENT"


def test_descendants_diamond(diamond_graph):
    assert diamond_graph.descendants("a") == ["b", "c", "d"]
    assert diamond_graph.descendants("b") == ["d"]
    assert diamond_graph.descendants("d") == []


def test_descendants_unknown_node(diamond_graph):
    with pytest.raises(ConformError):
        diamond_graph.descendants("nope")


def test_fanout_shares_upstream(fanout_graph):
    """All 4 territories share the same keyframe node — one upstream change
    dirties every territory package; a single-territory copy change does not."""
    assert fanout_graph.descendants("key") == ["pkg_br", "pkg_de", "pkg_fr", "pkg_jp"]
    assert fanout_graph.descendants("copy_de") == ["pkg_de"]
    assert len(fanout_graph) == 11  # 3 shared + 4 copy + 4 package
