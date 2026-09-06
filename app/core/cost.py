"""Cost and duration estimation — deterministic core.

Costs come from a static, versioned price table (USD per unit). Estimation is
pure arithmetic over node kinds and recipes — an LLM never estimates money.
All money is Decimal; no floats touch cost.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.domain.schemas import ModelBreakdown, NodeKind

# (per unit, unit size) — unit size normalises e.g. "per second of video".
PRICE_TABLE: dict[NodeKind, dict[str, Any]] = {
    NodeKind.SOURCE: {"model": "text", "modality": "text", "usd_per_unit": Decimal("0.0005"), "seconds": 2.0},
    NodeKind.SHOT_PLAN: {"model": "reasoning", "modality": "text", "usd_per_unit": Decimal("0.002"), "seconds": 4.0},
    NodeKind.KEYFRAME: {"model": "image", "modality": "image", "usd_per_unit": Decimal("0.04"), "seconds": 6.0},
    NodeKind.CLIP: {"model": "video", "modality": "video", "usd_per_unit": Decimal("0.35"), "seconds": 45.0},
    NodeKind.COPY: {"model": "text", "modality": "text", "usd_per_unit": Decimal("0.0005"), "seconds": 2.0},
    NodeKind.VOICEOVER: {"model": "tts", "modality": "audio", "usd_per_unit": Decimal("0.01"), "seconds": 8.0},
    NodeKind.MUSIC: {"model": "music", "modality": "music", "usd_per_unit": Decimal("0.05"), "seconds": 20.0},
    NodeKind.PACKAGE: {"model": "ffmpeg", "modality": "none", "usd_per_unit": Decimal("0"), "seconds": 5.0},
}


def estimate_nodes(kinds: list[NodeKind]) -> tuple[Decimal, float, list[ModelBreakdown]]:
    """Estimate cost and wall-time for building nodes of the given kinds.

    Wall-time assumes bounded parallelism of 4 — dirty nodes are built in
    waves, so seconds = ceil(count/4) * per-kind seconds, summed per kind.
    """
    total = Decimal("0")
    seconds = 0.0
    breakdown: dict[str, ModelBreakdown] = {}
    for kind in kinds:
        entry = PRICE_TABLE[kind]
        total += entry["usd_per_unit"]
        seconds += entry["seconds"] / 4.0
        key = entry["model"]
        if key not in breakdown:
            breakdown[key] = ModelBreakdown(
                model=key, modality=entry["modality"], node_count=0, cost_usd=Decimal("0")
            )
        b = breakdown[key]
        breakdown[key] = ModelBreakdown(
            model=b.model,
            modality=b.modality,
            node_count=b.node_count + 1,
            cost_usd=b.cost_usd + entry["usd_per_unit"],
        )
    return total, seconds, sorted(breakdown.values(), key=lambda m: m.model)
