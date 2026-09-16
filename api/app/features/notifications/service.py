"""Queueing and delivering outbound messages."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.ports import EmailDeliveryFailed, EmailSender
from app.features.notifications import domain, repository

log = get_logger(__name__)


async def enqueue_email(
    session: AsyncSession,
    *,
    recipient: str,
    subject: str,
    template_key: str,
    payload: dict[str, Any] | None,
    idempotency_key: str,
) -> None:
    """Queue in the caller's transaction.

    Writing the row beside the data that justified it is the point: a password
    reset that rolls back does not leave an email promising one.
    """
    await repository.enqueue(
        session,
        recipient=recipient,
        subject=subject,
        template_key=template_key,
        payload=payload,
        idempotency_key=idempotency_key,
    )


async def deliver_due(
    session: AsyncSession, *, sender: EmailSender, now: datetime, limit: int = 20
) -> tuple[int, int]:
    """Send whatever is due. Returns (sent, deferred).

    Each message is attempted independently: one bad address must not stop the
    rest of the queue.
    """
    sent = 0
    deferred = 0
    for message in await repository.claim_due(session, now=now, limit=limit):
        attempts = message.attempts + 1
        try:
            await sender.send(
                to=message.recipient,
                subject=message.subject,
                html=_render(message.template_key, message.payload),
            )
        except EmailDeliveryFailed as exc:
            if domain.should_retry(attempts=attempts):
                await repository.mark_retry(
                    session,
                    message.id,
                    attempts=attempts,
                    available_at=domain.next_available(attempts=attempts, now=now),
                    error=str(exc),
                )
                deferred += 1
            else:
                # Abandoned rather than retried forever, so somebody can see
                # that this one needs a person.
                log.warning("message abandoned", message_id=str(message.id), attempts=attempts)
                await repository.mark_failed(session, message.id, attempts=attempts, error=str(exc))
            continue
        await repository.mark_sent(session, message.id, at=now)
        sent += 1
    return sent, deferred


def _render(template_key: str, payload: dict[str, Any] | None) -> str:
    """Placeholder rendering.

    Real templates come with the Resend port; the queue, its idempotency and its
    backoff are what matter first, and they are testable without them.
    """
    data = payload or {}
    lines = "".join(f"<p>{key}: {value}</p>" for key, value in sorted(data.items()))
    return f"<h1>{template_key}</h1>{lines}"
