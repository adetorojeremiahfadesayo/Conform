"""Build engine — deterministic core.

Executes exactly the dirty subtree of an approved change, in topological
order, reusing every clean artifact byte-for-byte. Enforces the hard
invariants from AGENTS.md §8:

- refuses to build when the recorded approval graph_hash no longer matches
  the current graph (stale approvals never spend money)
- idempotent: re-running a completed build returns the same release
- a node whose fingerprint is unchanged is never regenerated
- failures are classified and retried per the retry taxonomy, on fresh
  attempt rows with parent_run_id lineage

Providers and the artifact store are injected as protocols, so this module
imports nothing generative. Every attempt emits NodeRunRecord rows; every
provider invocation emits a ProviderCallRecord.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from app.core.fingerprint import hash_graph
from app.core.graph import PipelineGraph
from app.core.retry import backoff_ms, classify_failure, should_retry
from app.domain.schemas import (
    Approval,
    ArtifactRecord,
    BuildResult,
    ConformError,
    ErrorClass,
    Node,
    NodeRunRecord,
    ProviderCallRecord,
    Release,
)


class Provider(Protocol):
    """A generative or packaging backend. Implementations live in
    app/providers/. The engine never constructs one itself."""

    kind_matches: tuple

    def generate(self, node: Node, parent_artifacts: dict[str, bytes]) -> tuple[bytes, str, ProviderCallRecord]:
        """Return (artifact bytes, content_type, provider call record).
        Raises ProviderFailure on failure."""


class ProviderFailure(Exception):
    def __init__(self, http_status: int | None, message: str):
        super().__init__(message)
        self.http_status = http_status
        self.message = message


class ArtifactStore(Protocol):
    def put(self, fingerprint: str, data: bytes, content_type: str) -> str: ...  # returns uri
    def fetch(self, uri: str) -> bytes: ...
    def exists(self, fingerprint: str) -> str | None: ...  # uri if present


def _new_build_id() -> str:
    from uuid import uuid4

    return f"build_{uuid4().hex[:12]}"


def run_build(
    *,
    graph: PipelineGraph,
    dirty_node_ids: list[str],
    approval: Approval,
    providers: dict[str, Provider],
    store: ArtifactStore,
    existing_releases: list[Release],
    completed_build_ids: set[str] | None = None,
    prior_build_id: str | None = None,
    sleep=lambda ms: None,
) -> BuildResult:
    """Execute an approved build.

    Invariants enforced here (tested):
      1. stale graph_hash => ConformError STALE_APPROVAL, zero provider calls
      2. idempotency: prior_build_id in completed_build_ids => return prior release
      3. unchanged fingerprint => artifact reused, never regenerated
    """
    current_hash = hash_graph(list(graph.nodes.values()))
    if approval.graph_hash != current_hash:
        raise ConformError(
            "STALE_APPROVAL",
            "graph changed since approval; re-estimate and re-approve before building",
            {"approved_hash": approval.graph_hash, "current_hash": current_hash},
        )

    if completed_build_ids and prior_build_id and prior_build_id in completed_build_ids:
        for rel in existing_releases:
            if rel.build_id == prior_build_id:
                return BuildResult(
                    build_id=prior_build_id,
                    change_id=approval.change_id,
                    release=rel,
                )

    build_id = prior_build_id or _new_build_id()
    dirty = set(dirty_node_ids)
    runs: list[NodeRunRecord] = []
    calls: list[ProviderCallRecord] = []
    artifacts: list[ArtifactRecord] = []
    artifact_bytes: dict[str, bytes] = {}
    retries = 0
    total_cost = Decimal("0")
    reused = 0
    rebuilt = 0

    order = [n for n in _topo_subset(graph, dirty)]

    for node in order:
        if node.node_id not in dirty:
            continue

        # Reuse path: an identical artifact already exists — never regenerate.
        existing_uri = store.exists(node.fingerprint)
        parent_artifacts = {p: artifact_bytes.get(p, b"") for p in node.parents}

        if existing_uri is not None:
            data = store.fetch(existing_uri)
            artifact_bytes[node.node_id] = data
            artifacts.append(
                ArtifactRecord(
                    fingerprint=node.fingerprint,
                    build_id=build_id,
                    node_id=node.node_id,
                    uri=existing_uri,
                    sha256=_sha(data),
                    bytes=len(data),
                    content_type=_content_type(node),
                )
            )
            runs.append(_run_record(node, build_id, status="ok", cache_hit=True))
            reused += 1
            continue

        provider = providers.get(node.kind.value)
        if provider is None:
            raise ConformError("NO_PROVIDER", f"no provider for node kind {node.kind.value}")

        attempt = 1
        parent_run_id: str | None = None
        while True:
            record = _run_record(node, build_id, status="running", attempt=attempt, parent_run_id=parent_run_id)
            try:
                data, content_type, call = provider.generate(node, parent_artifacts)
            except ProviderFailure as exc:
                classification = classify_failure(exc.http_status, exc.message)
                record.status = "failed"
                record.error_class = classification.error_class
                record.ended_at = record.started_at
                runs.append(record)
                if should_retry(classification, attempt):
                    sleep(backoff_ms(attempt))
                    parent_run_id = record.run_id
                    attempt += 1
                    retries += 1
                    continue
                raise ConformError(
                    "BUILD_FAILED",
                    f"node {node.node_id} failed ({classification.error_class.value}): {classification.reason}",
                    {"node_id": node.node_id, "attempts": attempt},
                ) from exc
            # success
            record.status = "ok"
            record.error_class = ErrorClass.NONE
            record.ended_at = record.started_at
            record.cost_usd = call.cost_usd
            record.bytes_out = len(data)
            runs.append(record)
            calls.append(call)
            total_cost += call.cost_usd

            uri = store.put(node.fingerprint, data, content_type)
            artifact_bytes[node.node_id] = data
            artifacts.append(
                ArtifactRecord(
                    fingerprint=node.fingerprint,
                    build_id=build_id,
                    node_id=node.node_id,
                    uri=uri,
                    sha256=_sha(data),
                    bytes=len(data),
                    content_type=content_type,
                )
            )
            rebuilt += 1
            break

    release = Release(
        release_id=f"release_{len(existing_releases) + 1:03d}",
        build_id=build_id,
        change_id=approval.change_id,
        artifacts=artifacts,
    )
    return BuildResult(
        build_id=build_id,
        change_id=approval.change_id,
        release=release,
        runs=runs,
        provider_calls=calls,
        nodes_rebuilt=rebuilt,
        nodes_reused=reused,
        total_cost_usd=total_cost,
        retries=retries,
    )


def _sha(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _content_type(node: Node) -> str:
    return {
        "source": "application/json",
        "shot_plan": "application/json",
        "keyframe": "image/png",
        "clip": "video/mp4",
        "copy": "application/json",
        "voiceover": "audio/wav",
        "music": "audio/wav",
        "package": "video/mp4",
    }.get(node.kind.value, "application/octet-stream")


def _run_record(
    node: Node,
    build_id: str,
    *,
    status: str,
    cache_hit: bool = False,
    attempt: int = 1,
    parent_run_id: str | None = None,
) -> NodeRunRecord:
    return NodeRunRecord(
        campaign_id=node.campaign_id,
        territory=node.territory,
        build_id=build_id,
        parent_run_id=parent_run_id,
        node_id=node.node_id,
        node_kind=node.kind,
        fingerprint=node.fingerprint,
        status=status,  # type: ignore[arg-type]
        cache_hit=cache_hit,
        attempt=attempt,
    )


def _topo_subset(graph: PipelineGraph, dirty: set[str]) -> list[Node]:
    """Topological order over the dirty subset (parents before children)."""
    ordered: list[Node] = []
    seen: set[str] = set()

    def visit(nid: str) -> None:
        if nid in seen:
            return
        seen.add(nid)
        for p in graph.nodes[nid].parents:
            if p in graph.nodes:
                visit(p)
        ordered.append(graph.nodes[nid])

    for nid in sorted(dirty):
        visit(nid)
    return ordered
