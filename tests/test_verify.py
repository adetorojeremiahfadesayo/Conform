"""Release verification (FR-7): byte-exact verdicts, tamper detection."""

from __future__ import annotations

from app.core.verify import sha256_bytes, verify_release
from app.domain.schemas import ArtifactRecord


class MemFetcher:
    def __init__(self, objects: dict[str, bytes]):
        self.objects = objects

    def fetch(self, uri: str) -> bytes:
        return self.objects[uri]


def _artifact(uri: str, data: bytes, node_id: str = "n") -> ArtifactRecord:
    return ArtifactRecord(
        fingerprint="f" * 64,
        build_id="build_x",
        node_id=node_id,
        uri=uri,
        sha256=sha256_bytes(data),
        bytes=len(data),
        content_type="application/octet-stream",
    )


def test_clean_release_verifies():
    objects = {"mem://a": b"payload-a", "mem://b": b"payload-b"}
    arts = [_artifact("mem://a", objects["mem://a"], "n1"), _artifact("mem://b", objects["mem://b"], "n2")]
    report = verify_release("release_001", arts, MemFetcher(objects))
    assert report.ok
    assert all(p["ok"] for p in report.per_artifact)


def test_single_flipped_byte_fails():
    good = b"approved-payload"
    tampered = bytearray(good)
    tampered[0] ^= 0x01  # flip one bit
    objects = {"mem://a": bytes(tampered)}
    report = verify_release("release_001", [_artifact("mem://a", good)], MemFetcher(objects))
    assert not report.ok
    assert report.per_artifact[0]["ok"] is False
    assert report.per_artifact[0]["actual_sha256"] != report.per_artifact[0]["expected_sha256"]


def test_missing_artifact_is_failed_verdict_not_crash():
    report = verify_release("release_001", [_artifact("mem://gone", b"x")], MemFetcher({}))
    assert not report.ok
    assert report.per_artifact[0]["ok"] is False
