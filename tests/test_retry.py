"""Retry taxonomy (FR-6.4) — pure classification, deterministic backoff."""

from __future__ import annotations

import pytest

from app.core.retry import MAX_ATTEMPTS, backoff_ms, classify_failure, should_retry
from app.domain.schemas import ErrorClass


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_transient_statuses(status):
    c = classify_failure(status)
    assert c.error_class == ErrorClass.TRANSIENT and c.retryable


@pytest.mark.parametrize("status", [400, 401, 403, 422])
def test_policy_statuses(status):
    c = classify_failure(status)
    assert c.error_class == ErrorClass.POLICY and not c.retryable


@pytest.mark.parametrize("status", [404, 410])
def test_permanent_statuses(status):
    c = classify_failure(status)
    assert c.error_class == ErrorClass.PERMANENT and not c.retryable


def test_message_markers_override():
    c = classify_failure(400, "request timeout contacting backend")
    assert c.error_class == ErrorClass.TRANSIENT


def test_unknown_is_permanent_fail_closed():
    c = classify_failure(418)
    assert c.error_class == ErrorClass.PERMANENT and not c.retryable


def test_retry_budget():
    c = classify_failure(503)
    assert should_retry(c, 1)
    assert should_retry(c, MAX_ATTEMPTS - 1)
    assert not should_retry(c, MAX_ATTEMPTS)


def test_backoff_deterministic():
    assert [backoff_ms(i) for i in (1, 2, 3)] == [500, 1000, 2000]
