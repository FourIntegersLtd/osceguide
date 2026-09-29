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
    escaped_fields = {key: escape(str(raw_value)) for key, raw_value in (payload or {}).items()}
    template = _TEMPLATES.get(template_key)
    if template is None:
        # An unknown key is a programming error, not a reason to send nothing:
        # the message still goes, and the key is visible in it.
        log.warning("no template for message", template_key=template_key)
        lines = "".join(
            f"<p>{key}: {escaped_value}</p>" for key, escaped_value in sorted(escaped_fields.items())
        )
        return f"{_LAYOUT_OPEN}<p>{escape(template_key)}</p>{lines}{_LAYOUT_CLOSE}"
    return f"{_LAYOUT_OPEN}{template(escaped_fields)}{_LAYOUT_CLOSE}"


_LAYOUT_OPEN = (
    '<div style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;'
    'max-width:34rem;margin:0 auto;padding:1.5rem;color:#111">'
)
_LAYOUT_CLOSE = '<p style="margin-top:2rem;color:#666;font-size:.875rem">OSCE Guide</p></div>'


def _password_reset(escaped_fields: dict[str, str]) -> str:
    """The body for a password-reset email, linking to the reset form with its token."""
    link = f"{get_settings().frontend_url.rstrip('/')}/reset-password?token={escaped_fields.get('token', '')}"
    return (
        "<h1>Reset your password</h1>"
        "<p>Use the link below to choose a new password. It expires in an hour, "
        "and using it signs you out everywhere else.</p>"
        f'<p><a href="{link}">Choose a new password</a></p>'
        "<p>If you did not ask for this, nothing has changed and you can ignore it.</p>"
    )


def _result_released(escaped_fields: dict[str, str]) -> str:
    """The body telling a candidate their sitting's outcome is ready to read."""
    link = f"{get_settings().frontend_url.rstrip('/')}/results/{escaped_fields.get('sitting_id', '')}"
    return (
        "<h1>Your result is available</h1>"
        "<p>Your institution has released the outcome for this sitting.</p>"
        f'<p><a href="{link}">Read your result</a></p>'
    )


def _invitation(escaped_fields: dict[str, str]) -> str:
    """The body inviting a new account holder to set a password and sign in."""
    link = (
        f"{get_settings().frontend_url.rstrip('/')}/accept-invitation?token={escaped_fields.get('token', '')}"
    )
    return (
        f"<h1>You have been invited to {escaped_fields.get('invited_to', '')}</h1>"
        "<p>An account has been created for this address. Choose a password to "
        "start using it. The link expires in seven days.</p>"
        f'<p><a href="{link}">Choose a password</a></p>'
        "<p>If you were not expecting this, you can ignore it and the account "
        "stays locked.</p>"
    )


def _practice_access_invitation(escaped_fields: dict[str, str]) -> str:
    """The body inviting someone with no account yet to practise an exam an organisation chose.

    Same token and link as `_invitation`: choosing the password is what accepts it, and the
    practice access is already attached to the account waiting behind the link.
    """
    link = (
        f"{get_settings().frontend_url.rstrip('/')}/accept-invitation?token={escaped_fields.get('token', '')}"
    )
    return (
        f"<h1>{escaped_fields.get('invited_to', '')} has given you practice access</h1>"
        f"<p>You can now practise <strong>{escaped_fields.get('exam_title', '')}</strong> on OSCE Guide. "
        "An account has been created for this address. Choose a password to start; "
        "the link expires in seven days.</p>"
        f'<p><a href="{link}">Choose a password</a></p>'
        "<p>If you were not expecting this, you can ignore it and the account stays locked.</p>"
    )


def _practice_access_granted(escaped_fields: dict[str, str]) -> str:
    """The body telling an existing account holder an organisation gave them an exam to practise."""
    link = f"{get_settings().frontend_url.rstrip('/')}/login"
    return (
        f"<h1>{escaped_fields.get('granted_by', '')} has given you practice access</h1>"
        f"<p>You can now practise <strong>{escaped_fields.get('exam_title', '')}</strong> "
        "with your existing OSCE Guide account.</p>"
        f'<p><a href="{link}">Sign in to start</a></p>'
    )


def _payment_receipt(escaped_fields: dict[str, str]) -> str:
    """The receipt, in the body of the email rather than attached.

    An attachment is the thing a mail client hides behind a click and a spam filter
    treats with suspicion. The full document is also at `/me/receipts/{id}/document`
    for anyone who wants to print it.

    `billing` owns what a receipt says and hands this module already-rendered fields;
    every value is still escaped here like any other template.
    """
    total = escaped_fields.get("amount_total", "")
    return (
        "<h1>Your receipt</h1>"
        f"<p>Thank you for your payment of {total}.</p>"
        f"<p>Receipt {escaped_fields.get('receipt_id', '')} — {escaped_fields.get('plan_label', '')}, "
        f"access until {escaped_fields.get('plan_end_date', '')}.</p>"
        "<p>You can open the full receipt in your account at any time.</p>"
    )


def _abuse_report(escaped_fields: dict[str, str]) -> str:
    """The body alerting support to a peer-practice abuse report."""
    return (
        "<h1>Peer-practice abuse report</h1>"
        f"<p>Session {escaped_fields.get('session_id', '')}, "
        f"reported by {escaped_fields.get('reporter', '')} "
        f"against {escaped_fields.get('reported', '')}.</p>"
        f"<p>{escaped_fields.get('message', '') or '(no message given)'}</p>"
    )


def _no_show_report(escaped_fields: dict[str, str]) -> str:
    """The body alerting support to a peer-practice no-show report."""
    return (
        "<h1>Peer-practice no-show report</h1>"
        f"<p>Session {escaped_fields.get('session_id', '')}, "
        f"reported by {escaped_fields.get('reporter', '')}.</p>"
        f"<p>{escaped_fields.get('message', '') or '(no message given)'}</p>"
    )


def _partner_spend_alert(escaped_fields: dict[str, str]) -> str:
    """The body telling the team a partner pilot's estimated spend crossed a threshold.

    Oracle: b2c `partner_spend_alert_email.html`, the same figures and the same
    disclaimer, which is what keeps it from being read as the partner's invoice.
    """
    return (
        f"<h1>{escaped_fields.get('partner', '')} pilot spend alert</h1>"
        f"<p>Estimated spend has reached {escaped_fields.get('estimated_spend', '')}, "
        f"past the {escaped_fields.get('threshold', '')} threshold, for "
        f"{escaped_fields.get('from_date', '')} to {escaped_fields.get('to_date', '')}.</p>"
        "<ul>"
        f"<li>Estimated clicks: {escaped_fields.get('estimated_clicks', '')} at "
        f"{escaped_fields.get('cost_per_click', '')} each</li>"
        f"<li>Gross revenue from acquired users: {escaped_fields.get('gross_revenue', '')}</li>"
        f"<li>Net margin: {escaped_fields.get('net_margin', '')}</li>"
        "</ul>"
        f"<p><small>{escaped_fields.get('disclaimer', '')}</small></p>"
    )


_TEMPLATES: dict[str, Callable[[dict[str, str]], str]] = {
    "password_reset": _password_reset,
    "payment_receipt": _payment_receipt,
    "invitation": _invitation,
    "practice_access_invitation": _practice_access_invitation,
    "practice_access_granted": _practice_access_granted,
    "candidate_result_released": _result_released,
    "peer_practice_abuse_report": _abuse_report,
    "peer_practice_no_show_report": _no_show_report,
    "partner_spend_alert": _partner_spend_alert,
}
