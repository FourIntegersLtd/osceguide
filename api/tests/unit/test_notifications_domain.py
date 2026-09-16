"""Delivering queued mail, and when to stop trying."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.features.notifications import domain

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def test_a_pending_message_is_due() -> None:
    assert domain.is_due(status="pending", available_at=NOW, now=NOW)


def test_a_message_scheduled_for_later_is_not_due() -> None:
    assert not domain.is_due(status="pending", available_at=NOW + timedelta(minutes=5), now=NOW)


@pytest.mark.parametrize("status", ["sent", "failed", "processing"])
def test_only_pending_messages_are_due(status: str) -> None:
    assert not domain.is_due(status=status, available_at=NOW, now=NOW)


def test_backoff_grows_with_each_attempt() -> None:
    """A provider that is down stays down for a while; retrying every second
    makes that worse for everyone."""
    delays = [domain.retry_delay(attempt) for attempt in range(1, 5)]
    assert delays == sorted(delays)
    assert delays[0] < delays[-1]


def test_backoff_is_capped() -> None:
    assert domain.retry_delay(99) == domain.MAX_RETRY_SECONDS


def test_a_message_is_abandoned_after_enough_attempts() -> None:
    """Abandoned, not retried forever: somebody has to look at it."""
    assert not domain.should_retry(attempts=domain.MAX_ATTEMPTS)
    assert domain.should_retry(attempts=domain.MAX_ATTEMPTS - 1)


def test_the_next_attempt_is_scheduled_from_now() -> None:
    assert domain.next_available(attempts=1, now=NOW) == NOW + timedelta(seconds=domain.retry_delay(1))
