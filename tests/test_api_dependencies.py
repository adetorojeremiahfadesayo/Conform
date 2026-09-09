"""API dependency lifecycle tests; coordinator state must survive concurrent requests."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import app.api.deps as deps


def test_concurrent_first_requests_share_one_coordinator(monkeypatch):
    created: list[object] = []

    def slow_factory():
        time.sleep(0.05)
        instance = object()
        created.append(instance)
        return instance

    monkeypatch.setattr(deps, "Coordinator", slow_factory)
    deps.reset_coordinator()

    with ThreadPoolExecutor(max_workers=8) as pool:
        coordinators = list(pool.map(lambda _: deps.get_coordinator(), range(8)))

    assert len(created) == 1
    assert all(coordinator is coordinators[0] for coordinator in coordinators)
    deps.reset_coordinator()
