"""Queueing and delivering outbound messages."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from html import escape
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.ports import EmailDeliveryFailed, EmailSender
from app.core.settings import get_settings
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
    reclaimed = await repository.reclaim_stale(session, before=domain.stale_claim_cutoff(now))
    if reclaimed:
        log.warning("reclaimed stranded messages", count=reclaimed)

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
    """The email body.

    Every value is escaped. The first version interpolated the payload straight
    into the markup, so a name containing a tag was injected into the message —
    and the "template" was the template's own key above a list of its
    variables, which is what a recipient would have received.
    """
    data = {key: escape(str(value)) for key, value in (payload or {}).items()}
    template = _TEMPLATES.get(template_key)
    if template is None:
        # An unknown key is a programming error, not a reason to send nothing:
        # the message still goes, and the key is visible in it.
        log.warning("no template for message", template_key=template_key)
        lines = "".join(f"<p>{key}: {value}</p>" for key, value in sorted(data.items()))
        return f"{_LAYOUT_OPEN}<p>{escape(template_key)}</p>{lines}{_LAYOUT_CLOSE}"
    return f"{_LAYOUT_OPEN}{template(data)}{_LAYOUT_CLOSE}"


_LAYOUT_OPEN = (
    '<div style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;'
    'max-width:34rem;margin:0 auto;padding:1.5rem;color:#111">'
)
_LAYOUT_CLOSE = '<p style="margin-top:2rem;color:#666;font-size:.875rem">OSCE Guide</p></div>'


def _password_reset(data: dict[str, str]) -> str:
    link = f"{get_settings().frontend_url.rstrip('/')}/reset-password?token={data.get('token', '')}"
    return (
        "<h1>Reset your password</h1>"
        "<p>Use the link below to choose a new password. It expires in an hour, "
        "and using it signs you out everywhere else.</p>"
        f'<p><a href="{link}">Choose a new password</a></p>'
        "<p>If you did not ask for this, nothing has changed and you can ignore it.</p>"
    )


def _result_released(data: dict[str, str]) -> str:
    link = f"{get_settings().frontend_url.rstrip('/')}/results/{data.get('sitting_id', '')}"
    return (
        "<h1>Your result is available</h1>"
        "<p>Your institution has released the outcome for this sitting.</p>"
        f'<p><a href="{link}">Read your result</a></p>'
    )


_TEMPLATES: dict[str, Callable[[dict[str, str]], str]] = {
    "password_reset": _password_reset,
    "candidate_result_released": _result_released,
}
