"""Storage for the outbox."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.models import OutboundMessage


async def enqueue(
    session: AsyncSession,
    *,
    recipient: str,
    subject: str,
    template_key: str,
    payload: dict[str, Any] | None,
    idempotency_key: str,
    channel: str = "email",
) -> OutboundMessage | None:
    """Queue a message, or do nothing if it is already queued.

    Returns None on a repeat rather than raising: the caller asked for a message
    to exist, and it does.
    """
    existing = await by_idempotency_key(session, idempotency_key)
    if existing is not None:
        return None
    message = OutboundMessage(
        recipient=recipient,
        subject=subject,
        template_key=template_key,
        payload=payload,
        idempotency_key=idempotency_key,
        channel=channel,
    )
    session.add(message)
    await session.flush()
    await session.refresh(message)
    return message


async def by_idempotency_key(session: AsyncSession, key: str) -> OutboundMessage | None:
    """The message already queued under this key, or nothing if none was."""
    stmt = select(OutboundMessage).where(OutboundMessage.idempotency_key == key)
    return (await session.execute(stmt)).scalar_one_or_none()


async def claim_due(session: AsyncSession, *, now: datetime, limit: int = 20) -> list[OutboundMessage]:
    """Take the next due messages, locking them against other workers.

    `FOR UPDATE SKIP LOCKED` so two workers never send the same email, and
    neither waits on the other.
    """
    stmt = (
        select(OutboundMessage)
        .where(OutboundMessage.status == "pending", OutboundMessage.available_at <= now)
        .order_by(OutboundMessage.available_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    messages = list((await session.execute(stmt)).scalars())
    if messages:
        await session.execute(
            update(OutboundMessage)
            .where(OutboundMessage.id.in_([message.id for message in messages]))
            .values(status="processing", claimed_at=now)
        )
    return messages


async def reclaim_stale(session: AsyncSession, *, before: datetime) -> int:
    """Return messages claimed before `before` to the queue.

    A worker that dies mid-batch leaves its claims `processing`, and the due
    index only covers `pending`, so without this they are invisible forever
    and nobody is told. Sending one twice is the lesser failure, and the
    idempotency key makes it unlikely anyway.
    """
    reclaimed = await session.execute(
        update(OutboundMessage)
        .where(
            OutboundMessage.status == "processing",
            OutboundMessage.claimed_at.is_not(None),
            OutboundMessage.claimed_at < before,
        )
        .values(status="pending", claimed_at=None)
        .returning(OutboundMessage.id)
    )
    return len(list(reclaimed.scalars()))


async def mark_sent(session: AsyncSession, message_id: uuid.UUID, *, at: datetime) -> None:
    """Record a successful delivery and release the claim."""
    await session.execute(
        update(OutboundMessage)
        .where(OutboundMessage.id == message_id)
        .values(status="sent", delivered_at=at, claimed_at=None, last_error=None)
    )


async def mark_retry(
    session: AsyncSession,
    message_id: uuid.UUID,
    *,
    attempts: int,
    available_at: datetime,
    error: str,
) -> None:
    """Release the claim and set a later `available_at`, so another worker retries it."""
    await session.execute(
        update(OutboundMessage)
        .where(OutboundMessage.id == message_id)
        .values(
            status="pending",
            attempts=attempts,
            available_at=available_at,
            claimed_at=None,
            last_error=error,
        )
    )


async def mark_failed(session: AsyncSession, message_id: uuid.UUID, *, attempts: int, error: str) -> None:
    """Give up on this message: it stays `failed` and is never retried again."""
    await session.execute(
        update(OutboundMessage)
        .where(OutboundMessage.id == message_id)
        .values(status="failed", attempts=attempts, claimed_at=None, last_error=error)
    )
