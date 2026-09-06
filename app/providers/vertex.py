"""Vertex AI providers — generative side of the boundary.

Each adapter calls exactly one Vertex AI media model via the google-genai
SDK (accepted SDK per hackathon rules) and records an honest ProviderCallRecord.
Any failure is raised as ProviderFailure with the real HTTP status so the
deterministic retry taxonomy classifies it — failures are never swallowed or
faked. Model IDs come from Config, never hardcoded here.
"""

from __future__ import annotations

import time
from decimal import Decimal
from uuid import uuid4

from app.config import Config
from app.core.builder import ProviderFailure
from app.domain.schemas import Node, ProviderCallRecord


class _VertexBase:
    provider_mode = "live"

    def __init__(self, config: Config, modality: str, model_attr: str, unit_cost: Decimal):
        self._config = config
        self._modality = modality
        self._unit_cost = unit_cost
        self._model = getattr(config, model_attr)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
            except ImportError as exc:
                raise ProviderFailure(None, "google-genai not installed") from exc
            self._client = genai.Client(
                vertexai=True,
                project=self._config.google_cloud_project,
                location=self._config.google_cloud_region,
            )
        return self._client

    def _call(self, fn, media_seconds: float = 0.0) -> tuple[bytes, ProviderCallRecord]:
        started = time.monotonic()
        try:
            data = fn(self._get_client(), self._model)
        except Exception as exc:
            status = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
            raise ProviderFailure(status, str(exc)[:200]) from exc
        return data, ProviderCallRecord(
            run_id=f"run_{uuid4().hex[:12]}",
            build_id="",
            model=self._model,
            modality=self._modality,
            region=self._config.google_cloud_region,
            latency_ms=int((time.monotonic() - started) * 1000),
            media_seconds=media_seconds,
            cost_usd=self._unit_cost,
            http_status=200,
        )


class VertexTextProvider(_VertexBase):
    """source / shot_plan / copy — Gemini text models with structured output."""

    content_type = "application/json"

    def __init__(self, config: Config, model_attr: str = "vertex_text_model"):
        super().__init__(config, "text", model_attr, Decimal("0.001"))

    def generate(self, node: Node, parent_artifacts: dict[str, bytes]) -> tuple[bytes, str, ProviderCallRecord]:
        prompt = str(node.inputs.get("prompt", ""))

        def fn(client, model) -> bytes:
            resp = client.models.generate_content(model=model, contents=prompt)
            return (resp.text or "").encode()

        data, call = self._call(fn)
        return data, self.content_type, call


class VertexImageProvider(_VertexBase):
    content_type = "image/png"

    def __init__(self, config: Config):
        super().__init__(config, "image", "vertex_image_model", Decimal("0.04"))

    def generate(self, node: Node, parent_artifacts: dict[str, bytes]) -> tuple[bytes, str, ProviderCallRecord]:
        prompt = str(node.inputs.get("prompt", ""))

        def fn(client, model) -> bytes:
            resp = client.models.generate_images(model=model, prompt=prompt)
            image = resp.generated_images[0].image
            return image.image_bytes

        data, call = self._call(fn)
        return data, self.content_type, call


class VertexVideoProvider(_VertexBase):
    content_type = "video/mp4"

    def __init__(self, config: Config):
        super().__init__(config, "video", "vertex_video_model", Decimal("0.35"))

    def generate(self, node: Node, parent_artifacts: dict[str, bytes]) -> tuple[bytes, str, ProviderCallRecord]:
        prompt = str(node.inputs.get("prompt", ""))
        seconds = float(node.recipe.get("duration_seconds", 6.0))

        def fn(client, model) -> bytes:
            op = client.models.generate_videos(model=model, prompt=prompt)
            while not op.done:
                time.sleep(5)
                op = client.operations.get(op)
            video = op.response.generated_videos[0].video
            return video.video_bytes or client.files.download(file=video.uri)

        data, call = self._call(fn, media_seconds=seconds)
        return data, self.content_type, call


class VertexTTSProvider(_VertexBase):
    content_type = "audio/wav"

    def __init__(self, config: Config):
        super().__init__(config, "audio", "vertex_tts_model", Decimal("0.01"))

    def generate(self, node: Node, parent_artifacts: dict[str, bytes]) -> tuple[bytes, str, ProviderCallRecord]:
        text = str(node.inputs.get("text", ""))

        def fn(client, model) -> bytes:
            resp = client.models.generate_content(
                model=model,
                contents=text,
                config={"response_modalities": ["AUDIO"]},
            )
            part = resp.candidates[0].content.parts[0]
            return part.inline_data.data

        data, call = self._call(fn)
        return data, self.content_type, call


class VertexMusicProvider(_VertexBase):
    content_type = "audio/wav"

    def __init__(self, config: Config):
        super().__init__(config, "music", "vertex_music_model", Decimal("0.05"))

    def generate(self, node: Node, parent_artifacts: dict[str, bytes]) -> tuple[bytes, str, ProviderCallRecord]:
        prompt = str(node.inputs.get("prompt", ""))

        def fn(client, model) -> bytes:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config={"response_modalities": ["AUDIO"]},
            )
            part = resp.candidates[0].content.parts[0]
            return part.inline_data.data

        data, call = self._call(fn)
        return data, self.content_type, call
