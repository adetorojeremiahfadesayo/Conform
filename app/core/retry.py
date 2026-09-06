"""Retry taxonomy — deterministic core.

Classifies provider failures into transient / permanent / policy and decides
whether an automatic retry is permitted. Classification is a pure function of
status codes and error strings — never LLM judgement. Retries run on a fresh
attempt row with parent_run_id pointing at the failed attempt, preserving the
full parent -> child execution lineage.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.schemas import ErrorClass

_TRANSIENT_STATUSES = {408, 409, 425, 429, 500, 502, 503, 504}
_POLICY_STATUSES = {400, 401, 403, 422}
_PERMANENT_STATUSES = {404, 410}
_TRANSIENT_SUBSTRINGS = ("timeout", "timed out", "unavailable", "rate limit", "overloaded", "deadline exceeded")

MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class FailureClassification:
    error_class: ErrorClass
    retryable: bool
    reason: str


def classify_failure(http_status: int | None, message: str = "") -> FailureClassification:
    """Pure classification of a provider failure."""
    lowered = message.lower()
    if any(s in lowered for s in _TRANSIENT_SUBSTRINGS):
        return FailureClassification(ErrorClass.TRANSIENT, True, f"transient marker in message: {message[:80]}")
    if http_status in _TRANSIENT_STATUSES:
        return FailureClassification(ErrorClass.TRANSIENT, True, f"http {http_status}")
    if http_status in _POLICY_STATUSES:
        return FailureClassification(ErrorClass.POLICY, False, f"http {http_status} — request rejected")
    if http_status in _PERMANENT_STATUSES:
        return FailureClassification(ErrorClass.PERMANENT, False, f"http {http_status}")
    return FailureClassification(ErrorClass.PERMANENT, False, f"unclassified failure (http {http_status})")


def should_retry(classification: FailureClassification, attempt: int) -> bool:
    return classification.retryable and attempt < MAX_ATTEMPTS


def backoff_ms(attempt: int) -> int:
    """Deterministic backoff: 500ms, 1000ms, 2000ms... no jitter in demo mode."""
    return 500 * (2 ** (attempt - 1))
