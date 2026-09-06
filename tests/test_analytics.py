"""Tests for Analytics and Synthetic History Seeding (PRD §5 FR-8.7, FR-10)."""

from __future__ import annotations

from decimal import Decimal

from app.agents.coordinator import Coordinator
from app.config import Config


def test_seed_history_and_analytics_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFORM_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("CONFORM_EVENTS_DB", str(tmp_path / "events.db"))

    coord = Coordinator(Config())

    # On startup, history must be seeded automatically
    summary = coord.analytics_summary()
    assert summary.nodes_rebuilt > 0
    assert summary.nodes_reused > 0
    assert summary.total_spend_usd > Decimal("0")
    assert summary.avoided_spend_usd > Decimal("0")
    assert 0.0 <= summary.cache_hit_rate <= 1.0
    assert len(summary.spend_by_model) > 0
    assert len(summary.spend_by_campaign) > 0
