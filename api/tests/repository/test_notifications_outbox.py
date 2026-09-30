"""Draining the outbox, and giving up sensibly."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications import domain, repository, service
from tests.support.fakes import RecordingEmailSender

pytestmark = pytest.mark.db


def now() -> datetime:
    """Read the clock when the test runs, not when the module is imported.

    `available_at` is stamped by Postgres `now()` — the transaction timestamp,
    which is later than import. A module-level constant is therefore *behind*
    every row it is compared against, and nothing is ever due. The gap is
    seconds in a suite this size, which is exactly long enough to look like a
    real failure.
    """
    return datetime.now(UTC)


async def queue(session: AsyncSession, key: str = "k1", recipient: str = "a@example.com") -> None:
    await service.enqueue_email(
        session,
        recipient=recipient,
        subject="Subject",
        template_key="t",
        payload={"x": 1},
        idempotency_key=key,
    )
    await session.flush()


async def test_a_queued_message_is_delivered(db_session: AsyncSession) -> None:
    await queue(db_session)
    sender = RecordingEmailSender()
    sent, deferred = await service.deliver_due(db_session, sender=sender, now=now())
    assert (sent, deferred) == (1, 0)
    assert sender.sent[0].to == "a@example.com"


async def test_a_delivered_message_is_not_sent_twice(db_session: AsyncSession) -> None:
    await queue(db_session)
    sender = RecordingEmailSender()
    await service.deliver_due(db_session, sender=sender, now=now())
    await db_session.flush()
    sent, _ = await service.deliver_due(db_session, sender=sender, now=now())
    assert sent == 0
    assert len(sender.sent) == 1


async def test_queueing_the_same_key_twice_queues_once(db_session: AsyncSession) -> None:
    """The slice that wrote it decides the key; a retry of its own work must not
    become a second email."""
    await queue(db_session, key="same")
    await queue(db_session, key="same")
    sender = RecordingEmailSender()
    sent, _ = await service.deliver_due(db_session, sender=sender, now=now())
    assert sent == 1


async def test_a_failure_is_retried_later_with_backoff(db_session: AsyncSession) -> None:
    await queue(db_session)
    sender = RecordingEmailSender(fail_times=1)
    sent, deferred = await service.deliver_due(db_session, sender=sender, now=now())
    assert (sent, deferred) == (0, 1)

    await db_session.flush()
    message = await repository.by_idempotency_key(db_session, "k1")
    assert message is not None
    assert message.status == "pending"
    assert message.attempts == 1
    assert message.available_at > now(), "a retry is scheduled, not immediate"


async def test_a_deferred_message_is_not_due_yet(db_session: AsyncSession) -> None:
    await queue(db_session)
    await service.deliver_due(db_session, sender=RecordingEmailSender(fail_times=1), now=now())
    await db_session.flush()

    sender = RecordingEmailSender()
    sent, _ = await service.deliver_due(db_session, sender=sender, now=now())
    assert sent == 0, "the backoff has not elapsed"

    later = now() + timedelta(seconds=domain.retry_delay(1) + 1)
    sent, _ = await service.deliver_due(db_session, sender=sender, now=later)
    assert sent == 1


async def test_a_message_is_abandoned_after_enough_failures(db_session: AsyncSession) -> None:
    """Abandoned, not retried forever: a queue that never gives up hides the
    fact that something needs a person."""
    await queue(db_session)
    sender = RecordingEmailSender(fail_times=domain.MAX_ATTEMPTS)
    at = now()
    for attempt in range(1, domain.MAX_ATTEMPTS + 1):
        await service.deliver_due(db_session, sender=sender, now=at)
        await db_session.flush()
        at = at + timedelta(seconds=domain.retry_delay(attempt) + 1)

    message = await repository.by_idempotency_key(db_session, "k1")
    assert message is not None
    assert message.status == "failed"
    assert message.attempts == domain.MAX_ATTEMPTS


async def test_one_bad_address_does_not_stop_the_queue(db_session: AsyncSession) -> None:
    await queue(db_session, key="bad", recipient="bad@example.com")
    await queue(db_session, key="good", recipient="good@example.com")
    sender = RecordingEmailSender(fail_times=1)

    sent, deferred = await service.deliver_due(db_session, sender=sender, now=now())
    assert sent == 1 and deferred == 1


async def test_a_stranded_claim_is_taken_back(db_session: AsyncSession) -> None:
    """A worker that dies between claiming and sending leaves `processing`
    rows. The due index only covers `pending`, so without a reaper the message
    is invisible to every later query and nobody is ever told."""

    await service.enqueue_email(
        db_session,
        recipient="stranded@example.com",
        subject="Hello",
        template_key="password_reset",
        payload={"token": "abc"},
        idempotency_key="stranded-1",
    )
    moment = now()
    claimed = await repository.claim_due(db_session, now=moment)
    assert [m.recipient for m in claimed] == ["stranded@example.com"]

    # Still held: a claim made a moment ago belongs to a live worker.
    assert await repository.reclaim_stale(db_session, before=domain.stale_claim_cutoff(moment)) == 0

    later = moment + timedelta(seconds=domain.CLAIM_TIMEOUT_SECONDS + 60)
    assert await repository.reclaim_stale(db_session, before=domain.stale_claim_cutoff(later)) == 1

    sender = RecordingEmailSender()
    sent, _ = await service.deliver_due(db_session, sender=sender, now=later)
    assert sent == 1
    assert [m.to for m in sender.sent] == ["stranded@example.com"]


async def test_an_email_body_escapes_what_it_is_given(db_session: AsyncSession) -> None:
    """The payload was interpolated into the markup unescaped, so a value
    carrying a tag was injected into the message."""
    await service.enqueue_email(
        db_session,
        recipient="escaped@example.com",
        subject="Hello",
        template_key="password_reset",
        payload={"token": '"><script>alert(1)</script>'},
        idempotency_key="escaped-1",
    )
    sender = RecordingEmailSender()
    await service.deliver_due(db_session, sender=sender, now=now())

    body = sender.sent[0].html
    assert "<script>" not in body
    assert "&lt;script&gt;" in body


async def test_a_password_reset_reads_as_an_email(db_session: AsyncSession) -> None:
    """It used to be the template's own key above a list of its variables,
    which is what the recipient would have read."""
    await service.enqueue_email(
        db_session,
        recipient="reader@example.com",
        subject="Reset your password",
        template_key="password_reset",
        payload={"token": "tok-123"},
        idempotency_key="readable-1",
    )
    sender = RecordingEmailSender()
    await service.deliver_due(db_session, sender=sender, now=now())

    body = sender.sent[0].html
    assert "Reset your password" in body
    assert "reset-password?token=tok-123" in body
    assert "password_reset" not in body, "the template key is not copy for a human"
