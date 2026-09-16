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
