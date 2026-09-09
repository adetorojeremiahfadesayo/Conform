"""Dependency wiring for the API layer — one Coordinator per app instance."""

from __future__ import annotations

from threading import Lock

from app.agents.coordinator import Coordinator

_coordinator: Coordinator | None = None
_coordinator_lock = Lock()


def get_coordinator() -> Coordinator:
    global _coordinator
    if _coordinator is None:
        with _coordinator_lock:
            if _coordinator is None:
                _coordinator = Coordinator()
    return _coordinator


def reset_coordinator() -> None:
    """Test hook — forces a fresh coordinator on next request."""
    global _coordinator
    _coordinator = None
