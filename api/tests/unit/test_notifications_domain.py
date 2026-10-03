"""Delivering queued mail, and when to stop trying."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.features.notifications import domain

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


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


def test_the_invitation_email_carries_the_link_and_the_board_wording() -> None:
    from app.features.notifications import service

    html = service._render("invitation", {"token": "tok123", "invited_to": "Kings <b>"})
    assert "/accept-invitation?token=tok123" in html
    assert "Kings &lt;b&gt; has invited you to OSCE Guide. Set a password to get started." in html
    assert ">Set your password</a>" in html
    assert "This link expires in 7 days." in html
