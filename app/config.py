"""Environment-driven configuration.

Never logs or exposes secret values. public_status() reports integration
*modes* only (live vs fallback), so the UI can label truthfully which parts
of the system are actually connected.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

try:
    import dotenv

    if "PYTEST_CURRENT_TEST" not in os.environ:
        dotenv.load_dotenv()
except Exception:
    pass


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Config:
    """Runtime configuration. All fields optional; absence = labelled fallback mode."""

    google_cloud_project: str = field(default_factory=lambda: _get("GOOGLE_CLOUD_PROJECT"))
    google_cloud_region: str = field(default_factory=lambda: _get("GOOGLE_CLOUD_REGION", "europe-west1"))

    vertex_text_model: str = field(default_factory=lambda: _get("VERTEX_TEXT_MODEL", "gemini-3.1-flash"))
    vertex_reasoning_model: str = field(default_factory=lambda: _get("VERTEX_REASONING_MODEL", "gemini-3-pro"))
    vertex_image_model: str = field(default_factory=lambda: _get("VERTEX_IMAGE_MODEL", "imagen-4"))
    vertex_video_model: str = field(default_factory=lambda: _get("VERTEX_VIDEO_MODEL", "veo-3.1-fast"))
    vertex_tts_model: str = field(default_factory=lambda: _get("VERTEX_TTS_MODEL", "chirp-3-hd"))
    vertex_music_model: str = field(default_factory=lambda: _get("VERTEX_MUSIC_MODEL", "lyria-2"))

    clickhouse_host: str = field(default_factory=lambda: _get("CLICKHOUSE_HOST"))
    clickhouse_port: int = field(default_factory=lambda: int(_get("CLICKHOUSE_PORT", "8443") or "8443"))
    clickhouse_user: str = field(default_factory=lambda: _get("CLICKHOUSE_USER", "default"))
    clickhouse_password: str = field(default_factory=lambda: _get("CLICKHOUSE_PASSWORD"))
    clickhouse_database: str = field(default_factory=lambda: _get("CLICKHOUSE_DATABASE", "default"))
    clickhouse_mcp_url: str = field(default_factory=lambda: _get("CLICKHOUSE_MCP_URL"))
    clickhouse_mcp_auth_token: str = field(default_factory=lambda: _get("CLICKHOUSE_MCP_AUTH_TOKEN"))

    artifact_bucket: str = field(default_factory=lambda: _get("ARTIFACT_BUCKET"))
    artifact_dir: str = field(default_factory=lambda: _get("CONFORM_ARTIFACT_DIR"))
    events_db: str = field(default_factory=lambda: _get("CONFORM_EVENTS_DB"))

    port: int = field(default_factory=lambda: int(_get("PORT", "8080") or "8080"))
    web_origin: str = field(default_factory=lambda: _get("WEB_ORIGIN", "http://localhost:5173"))

    build_budget_usd: str = field(default_factory=lambda: _get("BUILD_BUDGET_USD", "5.00"))
    fault_injection: str = field(default_factory=lambda: _get("FAULT_INJECTION", "off"))
    judge_mode: bool = field(default_factory=lambda: _get("JUDGE_MODE", "false").lower() == "true")

    @property
    def vertex_live(self) -> bool:
        """Vertex AI generation is only live with a project configured AND google-genai importable."""
        if not self.google_cloud_project:
            return False
        try:
            import google.genai  # noqa: F401
        except ImportError:
            return False
        return True

    @property
    def clickhouse_live(self) -> bool:
        return bool(self.clickhouse_host)

    @property
    def gcs_live(self) -> bool:
        return bool(self.artifact_bucket)

    @property
    def mcp_live(self) -> bool:
        return bool(self.clickhouse_mcp_url)

    def public_status(self) -> dict[str, str]:
        """Modes only — never values. Safe to return to the browser."""
        return {
            "vertex": "disabled_in_judge_mode" if self.judge_mode else (
                "configured_unverified" if self.vertex_live else "fallback_stub"
            ),
            "clickhouse_write": "disabled_in_judge_mode" if self.judge_mode else (
                "live" if self.clickhouse_live else "fallback_sqlite"
            ),
            "clickhouse_read_mcp": "configured_unverified" if self.mcp_live else "fallback_direct",
            "artifact_store": "gcs" if self.gcs_live else "local_filesystem",
            "budget_usd": self.build_budget_usd,
            "judge_mode": "locked_cached_demo" if self.judge_mode else "off",
        }


def load_config() -> Config:
    try:
        import dotenv

        if "PYTEST_CURRENT_TEST" not in os.environ:
            dotenv.load_dotenv(override=False)
    except Exception:
        pass
    return Config()
