"""Content-addressed fingerprinting — deterministic core.

fingerprint = SHA-256( canonical(node_id, kind, territory, inputs, recipe,
                                 sorted(parent_fingerprints)) )

Because parent fingerprints are mixed in, a change propagates transitively by
construction: if any ancestor changes, every descendant's fingerprint changes
without any graph walk at build time.

Determinism contract: same inputs + same recipe + same parents => same
fingerprint, across processes and serialisation round-trips. There is no LLM
involvement anywhere in this module.
"""

from __future__ import annotations

import hashlib

from app.core.canonical import canonicalize
from app.domain.schemas import Node, NodeSpec


def hash_payload(payload: dict) -> str:
    """SHA-256 of the canonical form of a dict. 64 lowercase hex chars."""
    return hashlib.sha256(canonicalize(payload).encode("utf-8")).hexdigest()


def fingerprint_node(node: NodeSpec, parent_fingerprints: dict[str, str]) -> str:
    """Compute a node's content fingerprint.

    parent_fingerprints maps node_id -> fingerprint for every parent in
    node.parents. Missing entries raise — never substitute a placeholder.
    """
    missing = [p for p in node.parents if p not in parent_fingerprints]
    if missing:
        raise KeyError(f"missing parent fingerprints for {node.node_id}: {missing}")
    return hash_payload(
        {
            "node_id": node.node_id,
            "kind": node.kind.value,
            "territory": node.territory,
            "inputs": node.inputs,
            "recipe": node.recipe,
            "parents": sorted(parent_fingerprints[p] for p in node.parents),
        }
    )


def hash_graph(nodes: list[Node]) -> str:
    """Order-independent hash of the entire graph state (ids + fingerprints).
    Used to pin an estimate/approval to the exact graph it was computed against."""
    return hash_payload({n.node_id: n.fingerprint for n in nodes})
