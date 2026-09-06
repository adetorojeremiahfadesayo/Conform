"""Dependency wiring for the API layer — one Coordinator per app instance."""

from __future__ import annotations

from app.agents.coordinator import Coordinator

_coordinator: Coordinator | None = None


def get_coordinator() -> Coordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = Coordinator()
    return _coordinator


def reset_coordinator() -> None:
    """Test hook — forces a fresh coordinator on next request."""
    global _coordinator
    _coordinator = None
