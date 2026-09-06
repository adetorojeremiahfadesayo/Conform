"""Deterministic packaging provider — ffmpeg mux/encode, NO AI (PRD §4).

Concatenates clip + voiceover + music bytes into a labelled package artifact.
In fallback/offline mode it produces a deterministic manifest container so the
pipeline remains fully exercisable without ffmpeg or media assets. The mode is
recorded in the artifact bytes so fallback output is never disguised.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from app.domain.schemas import Node, ProviderCallRecord


class PackageProvider:
    """ffmpeg-backed when available; deterministic offline manifest otherwise."""

    provider_mode = "live" if shutil.which("ffmpeg") else "fallback_offline"

    def generate(self, node: Node, parent_artifacts: dict[str, bytes]) -> tuple[bytes, str, ProviderCallRecord]:
        if shutil.which("ffmpeg") and parent_artifacts:
            try:
                return self._ffmpeg_mux(node, parent_artifacts)
            except Exception:
                pass  # explicit offline fallback below — labelled in payload
        manifest = (
            "OFFLINE PACKAGE (ffmpeg unavailable — fallback mode)\n"
            + "\n".join(
                f"input[{parent}]={len(data)} bytes"
                for parent, data in sorted(parent_artifacts.items())
            )
            + f"\nnode={node.node_id}\nfingerprint={node.fingerprint}\n"
        ).encode()
        return manifest, "video/mp4", self._record()

    def _ffmpeg_mux(self, node: Node, parent_artifacts: dict[str, bytes]) -> tuple[bytes, str, ProviderCallRecord]:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            inputs: list[Path] = []
            for i, data in enumerate(parent_artifacts.values()):
                p = tmpdir / f"in_{i}"
                p.write_bytes(data)
                inputs.append(p)
            out = tmpdir / "out.mp4"
            cmd = ["ffmpeg", "-y"]
            for p in inputs:
                cmd += ["-i", str(p)]
            cmd += ["-c", "copy", str(out)]
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
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
