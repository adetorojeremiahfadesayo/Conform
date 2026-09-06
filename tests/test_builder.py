"""Build engine invariants (FR-5, FR-6): approval gating, idempotency,
byte-exact reuse, retry lineage, and explicit failure."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.builder import ProviderFailure, run_build
from app.core.closure import compute_closure
from app.core.dirty import compute_estimate
from app.core.fingerprint import hash_graph
from app.domain.schemas import (
    Approval,
    Change,
    ChangeIntent,
    ChangeKind,
    ConformError,
    Node,
    ProviderCallRecord,
)


class SpyStore:
    """In-memory content-addressed store. put() is keyed by fingerprint, so a
    second put of the same fingerprint is a no-op — reuse is by construction."""

    def __init__(self):
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put(self, fingerprint: str, data: bytes, content_type: str) -> str:
        self.objects[fingerprint] = (data, content_type)
        return f"mem://{fingerprint}"

    def fetch(self, uri: str) -> bytes:
        return self.objects[uri.removeprefix("mem://")][0]

    def exists(self, fingerprint: str) -> str | None:
        return f"mem://{fingerprint}" if fingerprint in self.objects else None


class SpyProvider:
    """Records every generate() call; can be scripted to fail transiently."""

    def __init__(self, fail_times: int = 0, fail_status: int = 503):
        self.calls: list[str] = []
        self._fail_times = fail_times
        self._fail_status = fail_status

    def generate(self, node: Node, parent_artifacts: dict[str, bytes]):
        self.calls.append(node.node_id)
        if self._fail_times > 0:
            self._fail_times -= 1
            raise ProviderFailure(self._fail_status, "injected transient failure")
        data = f"artifact:{node.fingerprint}".encode()
        call = ProviderCallRecord(
            run_id=f"run_{uuid4().hex[:12]}",
            build_id="",
            model="test-model",
            modality="video",
            latency_ms=10,
            cost_usd=Decimal("0.35"),
        )
        return data, "application/octet-stream", call


def _approved_change_and_estimate(graph, node_id="b"):
    intent = ChangeIntent(kind=ChangeKind.ASSET_EDIT, node_id=node_id, new_inputs={"prompt": "new"})
    change = Change(kind=intent.kind, intent=intent)
    est = compute_estimate(change, graph, compute_closure(graph), Decimal("5.00"))
    approval = Approval(change_id=change.change_id, actor="producer (simulated)", graph_hash=est.graph_hash)
    return change, est, approval


def _providers(spy: SpyProvider) -> dict[str, SpyProvider]:
    return {k: spy for k in ("source", "shot_plan", "keyframe", "clip", "copy", "voiceover", "music", "package")}


def test_build_executes_dirty_only(diamond_graph):
    change, est, approval = _approved_change_and_estimate(diamond_graph, node_id="b")
    spy, store = SpyProvider(), SpyStore()
    result = run_build(
        graph=diamond_graph,
        dirty_node_ids=est.dirty_node_ids,
        approval=approval,
        providers=_providers(spy),
        store=store,
        existing_releases=[],
    )
    assert set(spy.calls) == {"b", "d"}  # b dirty -> d dirty; a, c untouched
    assert result.nodes_rebuilt == 2
    assert result.nodes_reused == 0  # nothing in the store yet
    assert result.release is not None
    assert {a.node_id for a in result.release.artifacts} == {"b", "d"}


def test_unchanged_fingerprint_is_reused_not_regenerated(diamond_graph):
    change, est, approval = _approved_change_and_estimate(diamond_graph, node_id="b")
    spy, store = SpyProvider(), SpyStore()
    first = run_build(
        graph=diamond_graph, dirty_node_ids=est.dirty_node_ids, approval=approval,
        providers=_providers(spy), store=store, existing_releases=[],
    )
    # Second build with the same graph: identical fingerprints -> all reuse.
    change2, est2, approval2 = _approved_change_and_estimate(diamond_graph, node_id="b")
    calls_before = len(spy.calls)
    second = run_build(
        graph=diamond_graph, dirty_node_ids=est2.dirty_node_ids, approval=approval2,
        providers=_providers(spy), store=store, existing_releases=[first.release],
    )
    assert len(spy.calls) == calls_before  # zero new provider calls
    assert second.nodes_reused == 2 and second.nodes_rebuilt == 0


def test_build_idempotent_returns_same_release(diamond_graph):
    change, est, approval = _approved_change_and_estimate(diamond_graph, node_id="b")
    spy, store = SpyProvider(), SpyStore()
    first = run_build(
        graph=diamond_graph, dirty_node_ids=est.dirty_node_ids, approval=approval,
        providers=_providers(spy), store=store, existing_releases=[],
    )
    again = run_build(
        graph=diamond_graph, dirty_node_ids=est.dirty_node_ids, approval=approval,
        providers=_providers(spy), store=store, existing_releases=[first.release],
        completed_build_ids={first.build_id}, prior_build_id=first.build_id,
    )
    assert again.build_id == first.build_id
    assert again.release.release_id == first.release.release_id


def test_stale_approval_refuses_before_any_spend(diamond_graph, diamond_specs):
    change, est, approval = _approved_change_and_estimate(diamond_graph, node_id="b")
    # Graph mutates after approval: fingerprints change -> hash mismatch.
    from app.core.graph import PipelineGraph
    from app.domain.schemas import NodeKind
    from tests.conftest import make_node

    mutated = [
        s if s.node_id != "c" else make_node("c", NodeKind.KEYFRAME, parents=["a"], inputs={"prompt": "changed"})
        for s in diamond_specs
    ]
    g2 = PipelineGraph(mutated)
    assert hash_graph(list(g2.nodes.values())) != approval.graph_hash

    spy, store = SpyProvider(), SpyStore()
    with pytest.raises(ConformError) as exc:
        run_build(
            graph=g2, dirty_node_ids=["b", "d"], approval=approval,
            providers=_providers(spy), store=store, existing_releases=[],
        )
    assert exc.value.error.code == "STALE_APPROVAL"
    assert spy.calls == []  # stale approvals never spend money


def test_transient_failure_retries_with_lineage(diamond_graph):
    change, est, approval = _approved_change_and_estimate(diamond_graph, node_id="b")
    spy, store = SpyProvider(fail_times=1, fail_status=503), SpyStore()
    result = run_build(
        graph=diamond_graph, dirty_node_ids=est.dirty_node_ids, approval=approval,
        providers=_providers(spy), store=store, existing_releases=[],
    )
    assert result.retries == 1
    failed = [r for r in result.runs if r.status == "failed"]
    ok = [r for r in result.runs if r.status == "ok" and r.attempt == 2]
    assert len(failed) == 1 and len(ok) == 1
    assert ok[0].parent_run_id == failed[0].run_id  # lineage preserved
    assert failed[0].error_class.value == "transient"


def test_permanent_failure_raises_explicit_error(diamond_graph):
    change, est, approval = _approved_change_and_estimate(diamond_graph, node_id="b")
    spy, store = SpyProvider(fail_times=99, fail_status=404), SpyStore()
    with pytest.raises(ConformError) as exc:
        run_build(
            graph=diamond_graph, dirty_node_ids=est.dirty_node_ids, approval=approval,
            providers=_providers(spy), store=store, existing_releases=[],
        )
    assert exc.value.error.code == "BUILD_FAILED"
    assert "permanent" in exc.value.error.message


def test_retry_budget_exhausted_raises(diamond_graph):
    change, est, approval = _approved_change_and_estimate(diamond_graph, node_id="b")
    spy, store = SpyProvider(fail_times=99, fail_status=503), SpyStore()
    with pytest.raises(ConformError) as exc:
        run_build(
            graph=diamond_graph, dirty_node_ids=est.dirty_node_ids, approval=approval,
            providers=_providers(spy), store=store, existing_releases=[],
        )
    assert exc.value.error.detail["attempts"] == 3  # MAX_ATTEMPTS
