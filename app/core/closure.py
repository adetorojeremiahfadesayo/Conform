"""Transitive closure maintenance — deterministic core.

The closure table (ancestor, descendant, depth) is recomputed when a graph is
built or mutated, so blast radius at query time is an indexed lookup — no
recursion on stage, matching the ClickHouse graph_closure table.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from app.core.graph import PipelineGraph


@dataclass(frozen=True)
class ClosureRow:
    ancestor: str
    descendant: str
    depth: int


def compute_closure(graph: PipelineGraph) -> list[ClosureRow]:
    """Full transitive closure with shortest-path depth per ancestor."""
    rows: list[ClosureRow] = []
    for nid in sorted(graph.nodes):
        depth: dict[str, int] = {}
        queue: deque[tuple[str, int]] = deque((c, 1) for c in graph.children.get(nid, []))
        while queue:
            cur, d = queue.popleft()
            if cur in depth and depth[cur] <= d:
                continue
            depth[cur] = d
            for c in graph.children.get(cur, []):
                queue.append((c, d + 1))
        rows.extend(ClosureRow(nid, desc, d) for desc, d in sorted(depth.items()))
    return rows


def blast_radius(closure: list[ClosureRow], sources: list[str]) -> dict[str, int]:
    """Dirty set for a set of directly-changed nodes: the sources themselves
    (depth 0) plus every descendant at its depth. Deterministic and total."""
    by_ancestor: dict[str, list[ClosureRow]] = {}
    for row in closure:
        by_ancestor.setdefault(row.ancestor, []).append(row)
    result: dict[str, int] = {}
    for src in sources:
        result.setdefault(src, 0)
        for row in by_ancestor.get(src, []):
            prev = result.get(row.descendant)
            if prev is None or row.depth < prev:
                result[row.descendant] = row.depth
    return dict(sorted(result.items()))
