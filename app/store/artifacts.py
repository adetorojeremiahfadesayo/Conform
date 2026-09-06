"""Content-addressed artifact store — GCS when configured, local files otherwise.

Artifacts are keyed by SHA-256 fingerprint: putting the same fingerprint twice
is a no-op, which is what makes byte-exact reuse structural rather than
accidental. Local fallback writes under output/artifacts/ and is labelled.
"""

from __future__ import annotations

from pathlib import Path

from app.config import Config


class LocalArtifactStore:
    mode = "local_filesystem"

    def __init__(self, root: Path | None = None):
        import os

        env_root = os.environ.get("CONFORM_ARTIFACT_DIR", "").strip()
        self._root = root or (Path(env_root) if env_root else Path("output/artifacts"))
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, fingerprint: str) -> Path:
        return self._root / fingerprint[:2] / fingerprint

    def put(self, fingerprint: str, data: bytes, content_type: str) -> str:
        path = self._path(fingerprint)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return f"local://{fingerprint}"

    def fetch(self, uri: str) -> bytes:
        return self._path(uri.removeprefix("local://")).read_bytes()

    def exists(self, fingerprint: str) -> str | None:
        return f"local://{fingerprint}" if self._path(fingerprint).exists() else None

    def tamper(self, uri_or_fp: str) -> bool:
        fp = uri_or_fp.removeprefix("local://")
        path = self._path(fp)
        if not path.exists():
            return False
        data = bytearray(path.read_bytes())
        if len(data) > 0:
            data[0] ^= 0xFF
        else:
            data.extend(b"tampered")
        path.write_bytes(bytes(data))
        return True


class GCSArtifactStore:
    mode = "gcs"

    def __init__(self, config: Config):
        try:
            from google.cloud import storage
        except ImportError as exc:
            raise RuntimeError("google-cloud-storage not installed") from exc
        self._bucket = storage.Client(project=config.google_cloud_project).bucket(config.artifact_bucket)

    def put(self, fingerprint: str, data: bytes, content_type: str) -> str:
        blob = self._bucket.blob(f"artifacts/{fingerprint}")
        if not blob.exists():
            blob.upload_from_string(data, content_type=content_type)
        return f"gs://{self._bucket.name}/artifacts/{fingerprint}"

    def fetch(self, uri: str) -> bytes:
        name = uri.split(f"gs://{self._bucket.name}/", 1)[1]
        return self._bucket.blob(name).download_as_bytes()

    def exists(self, fingerprint: str) -> str | None:
        blob = self._bucket.blob(f"artifacts/{fingerprint}")
        return f"gs://{self._bucket.name}/artifacts/{fingerprint}" if blob.exists() else None

    def tamper(self, uri_or_fp: str) -> bool:
        fp = uri_or_fp.split("artifacts/")[-1]
        blob = self._bucket.blob(f"artifacts/{fp}")
        if not blob.exists():
            return False
        data = bytearray(blob.download_as_bytes())
        if len(data) > 0:
            data[0] ^= 0xFF
        else:
            data.extend(b"tampered")
        blob.upload_from_string(bytes(data))
        return True


def build_store(config: Config):
    if config.gcs_live:
        return GCSArtifactStore(config)
    return LocalArtifactStore()
