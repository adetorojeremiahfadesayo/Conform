"""Append-only in-memory audit log with trace IDs.

Every workflow transition is recorded with a trace id so a demo session can be
reconstructed end to end. Simulated actor roles are recorded as simulated.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class AuditLog:
    def __init__(self):
        self.entries: list[dict[str, Any]] = []

    def record(self, event: str, **fields: Any) -> dict[str, Any]:
        entry = {
            "trace_id": f"trace_{uuid4().hex[:12]}",
            "event": event,
            "at": datetime.now(timezone.utc).isoformat(),
            **fields,
        }
        self.entries.append(entry)
        return entry

    def tail(self, n: int = 50) -> list[dict[str, Any]]:
        return self.entries[-n:]
