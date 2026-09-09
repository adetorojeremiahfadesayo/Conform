"""Build completion remains authoritative when telemetry persistence fails."""

from __future__ import annotations

from app.agents.coordinator import Coordinator
from app.config import Config
from app.domain.schemas import ChangeStatus


class FailingTelemetryWriter:
    mode = "live"

    def write_runs(self, _runs):
        raise RuntimeError("injected telemetry outage")

    def write_provider_calls(self, _calls):
        raise AssertionError("telemetry write should stop after the first failure")

    def write_artifacts(self, _artifacts):
        raise AssertionError("telemetry write should stop after the first failure")


def test_release_survives_telemetry_failure(tmp_path):
    coord = Coordinator(
        Config(
            google_cloud_project="",
            clickhouse_host="",
            artifact_bucket="",
            artifact_dir=str(tmp_path / "artifacts"),
            events_db=str(tmp_path / "events.db"),
        )
    )
    coord.writer = FailingTelemetryWriter()
    change = coord.submit_preset("eu_disclaimer_2026")
    coord.estimate_change(change.change_id)
    coord.approve(change.change_id, "producer (simulated)")

    result = coord.build(change.change_id)

    assert result.release is not None
    assert result.telemetry_status == "failed"
    assert result.telemetry_error == "event_store_write_failed"
    assert coord.changes[change.change_id].status == ChangeStatus.BUILD_COMPLETE
    assert any(entry["event"] == "build_telemetry_failed" for entry in coord.audit.entries)
