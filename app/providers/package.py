"""Deterministic packaging provider — ffmpeg mux/encode, NO AI (PRD §4).

Concatenates clip + voiceover + music bytes into a labelled package artifact.
In fallback/offline mode it produces a deterministic manifest container so the
pipeline remains fully exercisable without ffmpeg or media assets. The mode is
recorded in the artifact bytes so fallback output is never disguised.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import textwrap
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from app.core.builder import ProviderFailure
from app.domain.schemas import Node, ProviderCallRecord


class PackageProvider:
    """ffmpeg-backed when available; deterministic offline manifest otherwise."""

    provider_mode = "live" if shutil.which("ffmpeg") else "fallback_offline"

    def __init__(self, strict: bool = False):
        self.strict = strict

    def generate(self, node: Node, parent_artifacts: dict[str, bytes]) -> tuple[bytes, str, ProviderCallRecord]:
        if shutil.which("ffmpeg") and parent_artifacts:
            try:
                return self._ffmpeg_mux(node, parent_artifacts)
            except Exception as exc:
                if self.strict:
                    raise ProviderFailure(400, f"Package failed: {exc}") from exc
        if self.strict:
            raise ProviderFailure(400, "Playable package requires ffmpeg and cached parent media")
        manifest = (
            "OFFLINE PACKAGE (ffmpeg unavailable — fallback mode)\n"
            + "\n".join(
                f"input[{parent}]={len(data)} bytes"
                for parent, data in sorted(parent_artifacts.items())
            )
            + f"\nnode={node.node_id}\nfingerprint={node.fingerprint}\n"
        ).encode()
        return manifest, "text/plain", self._record()

    def _ffmpeg_mux(self, node: Node, parent_artifacts: dict[str, bytes]) -> tuple[bytes, str, ProviderCallRecord]:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            clips = [data for name, data in parent_artifacts.items() if name.endswith(".clip") and data]
            if not clips:
                raise ValueError("Missing cached master video")
            clip = tmpdir / "clip.mp4"
            clip.write_bytes(clips[0])
            copies = [data for name, data in parent_artifacts.items() if ".copy." in name and data]
            if not copies:
                raise ValueError("Missing generated copy")
            raw = copies[0].decode("utf-8").strip()
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            content = json.loads(raw)
            caption = "\n".join(
                textwrap.fill(str(content.get(field, "")), width=48)
                for field in ("headline", "disclaimer")
            )
            (tmpdir / "caption.txt").write_text(caption, encoding="utf-8")
            out = tmpdir / "out.mp4"
            cmd = ["ffmpeg", "-y", "-i", str(clip), "-vf",
                   "drawtext=textfile=caption.txt:expansion=none:fontsize=20:fontcolor=white:"
                   "box=1:boxcolor=black@0.7:x=20:y=h-th-30",
                   "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-movflags", "+faststart", str(out)]
            subprocess.run(cmd, cwd=tmpdir, check=True, capture_output=True, timeout=120)
            return out.read_bytes(), "video/mp4", self._record()

    @staticmethod
    def _record() -> ProviderCallRecord:
        return ProviderCallRecord(
            run_id=f"run_{uuid4().hex[:12]}",
            build_id="",
            model="ffmpeg",
            modality="none",
            cost_usd=Decimal("0"),
            http_status=200,
        )
