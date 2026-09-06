"""DAG construction and traversal — deterministic core.

Builds the pipeline graph from NodeSpecs, rejects cycles with an explicit
error, and computes fingerprints in topological order. Territory fan-out means
multiple territories share upstream nodes; the graph is keyed by node_id so
sharing is structural, not copied.
"""

from __future__ import annotations

from app.core.fingerprint import fingerprint_node
from app.domain.schemas import ConformError, Node, NodeSpec


class PipelineGraph:
    """A validated DAG of fingerprinted nodes."""

    def __init__(self, specs: list[NodeSpec]):
        self.nodes: dict[str, Node] = {}
        self.children: dict[str, list[str]] = {}
        self._build(specs)

    def _build(self, specs: list[NodeSpec]) -> None:
        by_id: dict[str, NodeSpec] = {}
        for s in specs:
            if s.node_id in by_id:
                raise ConformError("DUPLICATE_NODE", f"duplicate node_id: {s.node_id}")
            by_id[s.node_id] = s

        for s in specs:
            for p in s.parents:
                if p not in by_id:
                    raise ConformError(
                        "UNKNOWN_PARENT",
                        f"node {s.node_id} references unknown parent {p}",
                    )

        order = self._topological_order(by_id)
        fingerprints: dict[str, str] = {}
        children: dict[str, list[str]] = {nid: [] for nid in by_id}
        for nid in order:
            spec = by_id[nid]
            fp = fingerprint_node(spec, fingerprints)
            fingerprints[nid] = fp
            self.nodes[nid] = Node(**spec.model_dump(), fingerprint=fp)
            for p in spec.parents:
                children[p].append(nid)
        self.children = children

    @staticmethod
    def _topological_order(by_id: dict[str, NodeSpec]) -> list[str]:
        """Kahn's algorithm. Raises on cycles — never returns a partial order."""
        indegree = {nid: len(s.parents) for nid, s in by_id.items()}
        queue = sorted(nid for nid, d in indegree.items() if d == 0)
        order: list[str] = []
        child_map: dict[str, list[str]] = {nid: [] for nid in by_id}
        for nid, s in by_id.items():
            for p in s.parents:
                child_map[p].append(nid)
        while queue:
            nid = queue.pop(0)
            order.append(nid)
            for c in sorted(child_map[nid]):
                indegree[c] -= 1
                if indegree[c] == 0:
                    queue.append(c)
        if len(order) != len(by_id):
            remaining = sorted(nid for nid, d in indegree.items() if d > 0)
            raise ConformError(
                "CYCLE_DETECTED",
                "graph contains a cycle",
                {"nodes_in_cycle": remaining},
            )
        return order

    def descendants(self, node_id: str) -> list[str]:
        """All transitive descendants of a node (excluding itself), sorted."""
        if node_id not in self.nodes:
            raise ConformError("UNKNOWN_NODE", f"unknown node: {node_id}")
        seen: set[str] = set()
        stack = list(self.children.get(node_id, []))
        while stack:
            nid = stack.pop()
            if nid in seen:
                continue
            seen.add(nid)
            stack.extend(self.children.get(nid, []))
        return sorted(seen)

    def __len__(self) -> int:
        return len(self.nodes)
