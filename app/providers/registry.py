"""Provider registry — wires node kinds to providers based on Config.

Live Vertex providers are only constructed when Config.vertex_live is true;
otherwise every generative kind gets the labelled StubProvider. Packaging is
always the deterministic ffmpeg provider. The mapping is explicit — there is
no dynamic dispatch that could silently route to an unlabelled backend.
"""

from __future__ import annotations

from app.config import Config
from app.providers.base import StubProvider
from app.providers.package import PackageProvider


def build_providers(config: Config) -> dict:
    providers: dict[str, object] = {"package": PackageProvider(strict=config.vertex_live)}
    if config.vertex_live:
        from app.providers.vertex import (
            VertexImageProvider,
            VertexMusicProvider,
            VertexTextProvider,
            VertexTTSProvider,
            VertexVideoProvider,
        )

        providers.update(
            {
                "source": VertexTextProvider(config, "vertex_reasoning_model"),
                "shot_plan": VertexTextProvider(config, "vertex_reasoning_model"),
                "copy": VertexTextProvider(config, "vertex_text_model"),
                "keyframe": VertexImageProvider(config),
                "clip": VertexVideoProvider(config),
                "voiceover": VertexTTSProvider(config),
                "music": VertexMusicProvider(config),
            }
        )
    else:
        stub = StubProvider(fault_injection=config.fault_injection)
        for kind in ("source", "shot_plan", "copy", "keyframe", "clip", "voiceover", "music"):
            providers[kind] = stub
    return providers
