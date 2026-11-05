"""The outbox sends outside any transaction, a few at a time, and one failure stays one failure."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.features.notifications import repository, service
from tests.support.sessions import opener_for

pytestmark = pytest.mark.db


async def queue(session: AsyncSession, key: str, recipient: str) -> None:
    await service.enqueue_email(
        session,
        recipient=recipient,
        subject="Subject",
        template_key="password_reset",
        payload={"token": "x"},
        idempotency_key=key,
    )
    await session.flush()


class SlowSender:
    """Sleeps per send, like a provider round trip, and records the most sends in flight at once."""

    def __init__(self, delay: float = 0.05, explode_for: str | None = None) -> None:
        self.delay = delay
        self.explode_for = explode_for
        self.in_flight = 0
        self.peak = 0

    async def send(self, *, to: str, subject: str, html: str, reply_to: str | None = None) -> str:
        if to == self.explode_for:
            raise RuntimeError("provider blew up")
        self.in_flight += 1
        self.peak = max(self.peak, self.in_flight)
        await asyncio.sleep(self.delay)
        self.in_flight -= 1
        return "id"


async def test_250_queued_messages_drain_in_three_runs_at_batch_100_and_concurrency_5(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "outbox_delivery_batch", 100)
    monkeypatch.setattr(settings, "outbox_send_concurrency", 5)
    for index in range(250):
        await queue(db_session, f"bulk-{index}", f"u{index}@example.com")
    sender = SlowSender()

    runs = 0
    total = 0
    while total < 250 and runs < 5:
        sent, _ = await service.deliver_due(opener_for(db_session), sender=sender, now=datetime.now(UTC))
        total += sent
        runs += 1

    assert (total, runs) == (250, 3)
    assert sender.peak == 5, "sends overlap, a few at a time"


async def test_a_sender_that_raises_retries_only_that_message(db_session: AsyncSession) -> None:
    await queue(db_session, "boom", "boom@example.com")
    await queue(db_session, "fine", "fine@example.com")
    sender = SlowSender(delay=0, explode_for="boom@example.com")

    sent, deferred = await service.deliver_due(opener_for(db_session), sender=sender, now=datetime.now(UTC))

    assert (sent, deferred) == (1, 1)
    await db_session.flush()
    boom = await repository.by_idempotency_key(db_session, "boom")
    fine = await repository.by_idempotency_key(db_session, "fine")
    assert boom is not None and fine is not None
    assert (boom.status, boom.attempts, boom.last_error) == ("pending", 1, "provider blew up")
    assert fine.status == "sent"


async def test_no_session_is_open_while_a_message_is_being_sent(db_session: AsyncSession) -> None:
    """The claim commits before the first send and the outcomes are written after the last."""
    await queue(db_session, "held", "held@example.com")
    open_sessions = 0
    during_send: list[int] = []

    @asynccontextmanager
    async def counting_opener() -> AsyncIterator[AsyncSession]:
        nonlocal open_sessions
        open_sessions += 1
        try:
            yield db_session
        finally:
            open_sessions -= 1

    class Probe:
        async def send(self, *, to: str, subject: str, html: str, reply_to: str | None = None) -> str:
            during_send.append(open_sessions)
            return "id"

    sent, _ = await service.deliver_due(counting_opener, sender=Probe(), now=datetime.now(UTC))

    assert sent == 1
    assert during_send == [0]


async def test_a_template_that_cannot_render_fails_only_its_own_message(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A template raising something other than `UnknownTemplate` must not lose the batch's other sends."""

    def broken(fields: dict[str, str]) -> str:
        raise KeyError("missing")

    monkeypatch.setitem(service._TEMPLATES, "broken_for_test", broken)
    await service.enqueue_email(
        db_session,
        recipient="bad@example.com",
        subject="s",
        template_key="broken_for_test",
        payload={},
        idempotency_key="broken",
    )
    await queue(db_session, "good", "good@example.com")

    sent, _ = await service.deliver_due(
        opener_for(db_session), sender=SlowSender(delay=0), now=datetime.now(UTC)
    )

    assert sent == 1
    await db_session.flush()
    broken_row = await repository.by_idempotency_key(db_session, "broken")
    good_row = await repository.by_idempotency_key(db_session, "good")
    assert broken_row is not None and good_row is not None
    assert (broken_row.status, good_row.status) == ("failed", "sent")


async def test_one_outcome_that_cannot_be_recorded_does_not_lose_the_others(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await queue(db_session, "stuck", "stuck@example.com")
    await queue(db_session, "fine", "fine@example.com")
    real_mark_sent = repository.mark_sent

    async def flaky(session: AsyncSession, message_id, *, at):  # type: ignore[no-untyped-def]
        stuck = await repository.by_idempotency_key(session, "stuck")
        if stuck is not None and stuck.id == message_id:
            raise RuntimeError("database blip")
        await real_mark_sent(session, message_id, at=at)

    monkeypatch.setattr(repository, "mark_sent", flaky)

    sent, _ = await service.deliver_due(
        opener_for(db_session), sender=SlowSender(delay=0), now=datetime.now(UTC)
    )

    assert sent == 1
    await db_session.flush()
    db_session.expire_all()
    stuck_row = await repository.by_idempotency_key(db_session, "stuck")
    fine_row = await repository.by_idempotency_key(db_session, "fine")
    assert stuck_row is not None and fine_row is not None
    assert (stuck_row.status, fine_row.status) == ("processing", "sent")
