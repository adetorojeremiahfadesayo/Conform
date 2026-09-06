"""Provider base — generative side of the boundary.

Defines the Provider contract the build engine consumes and the shared
stub provider used whenever a live Vertex integration is not configured.
Stub output is labelled in the recipe log so fallback mode is never
disguised as live generation.
"""

from __future__ import annotations

import time
from decimal import Decimal
from uuid import uuid4

from app.core.builder import ProviderFailure  # noqa: F401  (re-exported contract)
from app.domain.schemas import Node, ProviderCallRecord

_STUB_COSTS: dict[str, Decimal] = {
    "source": Decimal("0.0005"),
    "shot_plan": Decimal("0.002"),
    "keyframe": Decimal("0.04"),
    "clip": Decimal("0.35"),
    "copy": Decimal("0.0005"),
    "voiceover": Decimal("0.01"),
    "music": Decimal("0.05"),
    "package": Decimal("0"),
}

_STUB_CONTENT_TYPES: dict[str, str] = {
    "source": "application/json",
    "shot_plan": "application/json",
    "keyframe": "image/png",
    "clip": "video/mp4",
    "copy": "application/json",
    "voiceover": "audio/wav",
    "music": "audio/wav",
    "package": "video/mp4",
}

_STUB_MODALITIES: dict[str, str] = {
    "source": "text",
    "shot_plan": "text",
    "keyframe": "image",
    "clip": "video",
    "copy": "text",
    "voiceover": "audio",
    "music": "music",
    "package": "none",
}


class StubProvider:
    """Deterministic offline generator. Produces stable, content-addressed
    bytes derived from the node fingerprint, and records honest synthetic
    costs. Used when Vertex is not configured — always labelled as a stub."""

    provider_mode = "fallback_stub"

    def __init__(self, fault_injection: str = "off"):
        self._fault_injection = fault_injection
        self._injected = False

    def set_fault_injection(self, mode: str) -> None:
        self._fault_injection = mode
        self._injected = False

    def generate(self, node: Node, parent_artifacts: dict[str, bytes]) -> tuple[bytes, str, ProviderCallRecord]:
        # Demo fault-injection switch: one transient timeout, exactly once.
        if self._fault_injection == "transient_once" and not self._injected and node.kind.value == "clip":
            self._injected = True
            raise ProviderFailure(503, "injected transient provider timeout (demo switch)")
        started = time.monotonic()
        payload = (
            f"STUB ARTIFACT (fallback mode — no live Vertex call)\n"
            f"node={node.node_id}\nkind={node.kind.value}\nfingerprint={node.fingerprint}\n"
        ).encode()
        call = ProviderCallRecord(
            run_id=f"run_{uuid4().hex[:12]}",
            build_id="",
            model=f"stub/{node.recipe.get('model', 'unknown')}",
            modality=_STUB_MODALITIES[node.kind.value],
            latency_ms=int((time.monotonic() - started) * 1000),
            cost_usd=_STUB_COSTS[node.kind.value],
            http_status=200,
        )
        return payload, _STUB_CONTENT_TYPES[node.kind.value], call
