"""Release verification — deterministic core.

Re-downloads every artifact, re-hashes bytes, and compares against the
recorded SHA-256. Byte-exact verdicts only; a single flipped byte fails.
No LLM involvement — verification is pure hashing.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

from app.domain.schemas import ArtifactRecord, ConformError, VerificationReport


class ArtifactFetcher(Protocol):
    """Anything that can return artifact bytes by uri (GCS, local fs, test stub)."""

    def fetch(self, uri: str) -> bytes: ...


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_release(
    release_id: str,
    artifacts: list[ArtifactRecord],
    fetcher: ArtifactFetcher,
) -> VerificationReport:
    per_artifact: list[dict] = []
    all_ok = True
    for art in artifacts:
        try:
            actual = sha256_bytes(fetcher.fetch(art.uri))
            ok = actual == art.sha256
        except ConformError:
            raise
        except Exception as exc:  # fetch failure is an explicit failed verdict
            ok = False
            actual = f"fetch_error: {type(exc).__name__}"
        all_ok = all_ok and ok
        per_artifact.append(
            {
                "node_id": art.node_id,
                "uri": art.uri,
                "expected_sha256": art.sha256,
                "actual_sha256": actual,
                "ok": ok,
            }
        )
    return VerificationReport(release_id=release_id, ok=all_ok, per_artifact=per_artifact)
