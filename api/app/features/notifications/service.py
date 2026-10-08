"""Queueing and delivering outbound messages."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from html import escape
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.ports import EmailDeliveryFailed, EmailSender
from app.core.settings import get_settings
from app.features.notifications import domain, repository
from app.features.notifications.models import OutboundMessage

log = get_logger(__name__)

# Messages sent per minute-run. 20 meant 500 invitations took 25 minutes (S-25).
DELIVERY_BATCH = 100


class UnknownTemplate(LookupError):
    """A queued message names a template that does not exist: a bug in whoever queued it."""


async def enqueue_email(
    session: AsyncSession,
    *,
    recipient: str,
    subject: str,
    template_key: str,
    payload: dict[str, Any] | None,
    idempotency_key: str,
) -> bool:
    """Queue in the caller's transaction. True when queued now, False when that key was already queued.

    Writing the row beside the data that justified it is the point: a password
    reset that rolls back does not leave an email promising one.
    """
    message = await repository.enqueue(
        session,
        recipient=recipient,
        subject=subject,
        template_key=template_key,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    return message is not None


async def deliver_due(
    session: AsyncSession, *, sender: EmailSender, now: datetime, limit: int = DELIVERY_BATCH
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
            html = _render(message.template_key, message.payload)
        except UnknownTemplate as exc:
            # Retrying cannot help: the code that queued it is wrong. Failed, so the console
            # lists it, rather than a debug-style email to a real person.
            log.error(
                "message names no template", message_id=str(message.id), template_key=message.template_key
            )
            await repository.mark_failed(session, message.id, attempts=attempts, error=str(exc))
            continue
        try:
            await sender.send(to=message.recipient, subject=message.subject, html=html)
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
                # that this one needs a person: an error, so it reaches Sentry,
                # and a `failed` row, which the console lists with a retry.
                log.error("message abandoned", message_id=str(message.id), attempts=attempts)
                await repository.mark_failed(session, message.id, attempts=attempts, error=str(exc))
            continue
        await repository.mark_sent(session, message.id, at=now)
        sent += 1
    return sent, deferred


async def list_undelivered(session: AsyncSession, *, limit: int) -> list[OutboundMessage]:
    """What the worker gave up on, for the console: newest first."""
    return await repository.failed_messages(session, limit=limit)


async def retry_undelivered(session: AsyncSession, message_id: uuid.UUID, *, now: datetime) -> bool:
    """Send an abandoned message again. False when it is not (or no longer)
    abandoned: unknown, sent, or already queued again."""
    return await repository.requeue_failed(session, message_id, now=now)


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
        raise UnknownTemplate(f"No template for {template_key!r}")
    return f"{_LAYOUT_OPEN}{template(escaped_fields)}{_LAYOUT_CLOSE}"


_LAYOUT_OPEN = (
    '<div style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;'
    'max-width:34rem;margin:0 auto;padding:2rem 1.5rem;color:#1D1D1F;font-size:15px;line-height:1.55">'
)
_LAYOUT_CLOSE = '<p style="margin-top:2rem;color:#6E6E73;font-size:13px">OSCE Guide</p></div>'

_BODY = "margin:0 0 16px;color:#1D1D1F"
_META = "margin:16px 0 0;color:#6E6E73;font-size:13px"


def _button(link: str, label: str) -> str:
    """The email's one primary action, the only place the institution colour appears."""
    return (
        f'<p style="margin:24px 0 0"><a href="{link}" style="display:inline-block;background:#090C85;'
        'color:#fff;text-decoration:none;padding:10px 20px;border-radius:10px;font-weight:500"'
        f">{label}</a></p>"
    )


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


def _email_change(escaped_fields: dict[str, str]) -> str:
    """The body for the link that confirms a new sign-in address."""
    link = f"{get_settings().frontend_url.rstrip('/')}/confirm-email?token={escaped_fields.get('token', '')}"
    return (
        "<h1>Confirm your new email address</h1>"
        "<p>Use the link below to make this the address you sign in with. It expires in an hour, "
        "and using it signs you out everywhere.</p>"
        f'<p><a href="{link}">Confirm this address</a></p>'
        "<p>If you did not ask for this, nothing has changed and you can ignore it.</p>"
    )


def _email_change_requested(escaped_fields: dict[str, str]) -> str:
    """The body sent to the current address when a change to a new one is asked for."""
    return (
        "<h1>A change of email was requested</h1>"
        "<p>Someone asked to move your OSCE Guide account to "
        f"{escaped_fields.get('new_email', 'a new address')}. Nothing changes until that address "
        "confirms.</p>"
        "<p>If this was not you, reset your password now.</p>"
    )


def _email_changed_notice(escaped_fields: dict[str, str]) -> str:
    """The body sent to the old address once an account has moved to a new one."""
    return (
        "<h1>Your email address was changed</h1>"
        "<p>Your OSCE Guide account now signs in with "
        f"{escaped_fields.get('new_email', 'a new address')}.</p>"
        "<p>If this was not you, reset your password straight away or contact support.</p>"
    )


def _result_released(escaped_fields: dict[str, str]) -> str:
    """The body telling a candidate their sitting's outcome is ready to read."""
    link = (
        f"{get_settings().frontend_url.rstrip('/')}/app/{escaped_fields.get('org_slug', '')}"
        f"/trainee/results/{escaped_fields.get('sitting_id', '')}"
    )
    institution = escaped_fields.get("org_name") or "Your institution"
    return (
        "<h1>Your result is available</h1>"
        f"<p>{institution} has released the outcome for this sitting.</p>"
        f'<p><a href="{link}">Read your result</a></p>'
    )


def _invitation(escaped_fields: dict[str, str]) -> str:
    """The body inviting a new account holder to set a password and sign in."""
    link = (
        f"{get_settings().frontend_url.rstrip('/')}/accept-invitation?token={escaped_fields.get('token', '')}"
    )
    return (
        f'<h1 style="margin:0 0 16px;font-size:22px;font-weight:600">'
        f"You are invited to {escaped_fields.get('invited_to', '')}</h1>"
        f'<p style="{_BODY}">{escaped_fields.get("invited_to", "")} has invited you to OSCE Guide. '
        "Set a password to get started.</p>"
        f"{_button(link, 'Set your password')}"
        f'<p style="{_META}">This link expires in 7 days. Not expecting this? You can ignore this '
        "email and the account stays locked.</p>"
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
        f'<h1 style="margin:0 0 16px;font-size:22px;font-weight:600">'
        f"{escaped_fields.get('invited_to', '')} has given you practice access</h1>"
        f'<p style="{_BODY}">You can now practise <strong>{escaped_fields.get("exam_title", "")}</strong> '
        "on OSCE Guide. Set a password to get started.</p>"
        f"{_button(link, 'Set your password')}"
        f'<p style="{_META}">This link expires in 7 days. Not expecting this? You can ignore this '
        "email and the account stays locked.</p>"
    )


def _practice_access_granted(escaped_fields: dict[str, str]) -> str:
    """The body telling an existing account holder an organisation gave them an exam to practise."""
    # The practice area, not /login: a signed-in person lands there, and sign-in sends the rest back.
    link = f"{get_settings().frontend_url.rstrip('/')}/app/me"
    return (
        f'<h1 style="margin:0 0 16px;font-size:22px;font-weight:600">'
        f"{escaped_fields.get('granted_by', '')} has given you practice access</h1>"
        f'<p style="{_BODY}">You can now practise <strong>{escaped_fields.get("exam_title", "")}</strong> '
        "with your existing OSCE Guide account. There is nothing new to set up.</p>"
        f"{_button(link, 'Start practising')}"
    )


def _entitlement_expiring(escaped_fields: dict[str, str]) -> str:
    """The body warning that bought access ends soon (S-12)."""
    link = f"{get_settings().frontend_url.rstrip('/')}/app/me/settings"
    return (
        f'<h1 style="margin:0 0 16px;font-size:22px;font-weight:600">'
        f"Your {escaped_fields.get('exam_title', '')} access ends on {escaped_fields.get('ends_on', '')}</h1>"
        f'<p style="{_BODY}">Your practice history stays on your account. Once your access has ended '
        "you can buy more from your settings and carry on where you left off.</p>"
        f"{_button(link, 'Open your settings')}"
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
    link = f"{get_settings().frontend_url.rstrip('/')}/app/me/settings"
    return (
        "<h1>Your receipt</h1>"
        f"<p>Thank you for your payment of {total}.</p>"
        f"<p>Receipt {escaped_fields.get('receipt_id', '')} — {escaped_fields.get('plan_label', '')}, "
        f"access until {escaped_fields.get('plan_end_date', '')}.</p>"
        f"{_button(link, 'Open your receipts')}"
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


def _in_words(iso: str) -> str:
    """`2026-10-09T14:30:00+00:00` as "Friday 9 October 2026, 14:30 UTC"; anything else is left as given."""
    try:
        moment = datetime.fromisoformat(iso).astimezone(UTC)
    except ValueError:
        return iso
    return f"{moment:%A} {moment.day} {moment:%B %Y}, {moment:%H:%M} UTC"


def _marketplace_session_reminder(escaped_fields: dict[str, str]) -> str:
    """The body reminding both sides of a peer practice session it starts in an hour.

    `escaped_fields` carries the payload `service_reminders.py` builds: the recipient's
    own display name, their partner's, when the session starts, and which exam it is for.
    """
    link = (
        f"{get_settings().frontend_url.rstrip('/')}/app/me/marketplace/session/"
        f"{escaped_fields.get('peer_session_id', '')}"
    )
    return (
        "<h1>Your practice session starts in an hour</h1>"
        f"<p>Hi {escaped_fields.get('username', 'there')}, you are practising with "
        f"{escaped_fields.get('partner_username', 'your partner')} at "
        f"{_in_words(escaped_fields.get('scheduled_at', ''))}.</p>"
        f'<p><a href="{link}">Open the session</a></p>'
    )


def _inactive_user_engagement(escaped_fields: dict[str, str]) -> str:
    """The body nudging a signed-up but never-practised person to try their first station.

    `escaped_fields` carries the payload `identity.service_engagement` builds: the
    recipient's display name and the exam their account is set to.
    """
    link = f"{get_settings().frontend_url.rstrip('/')}/dashboard"
    exam_name = escaped_fields.get("exam_name", "")
    first_station = f"first {exam_name} station" if exam_name else "first station"
    return (
        f"<h1>Ready to complete your {first_station}?</h1>"
        f"<p>Hi {escaped_fields.get('display_name', 'Doctor')}, you signed up but have not yet "
        "run through a practice station. It only takes a few minutes to see how it works.</p>"
        f'<p><a href="{link}">Start your first station</a></p>'
    )


_TEMPLATES: dict[str, Callable[[dict[str, str]], str]] = {
    "password_reset": _password_reset,
    "email_change": _email_change,
    "email_changed_notice": _email_changed_notice,
    "email_change_requested": _email_change_requested,
    "payment_receipt": _payment_receipt,
    "entitlement_expiring": _entitlement_expiring,
    "invitation": _invitation,
    "practice_access_invitation": _practice_access_invitation,
    "practice_access_granted": _practice_access_granted,
    "candidate_result_released": _result_released,
    "peer_practice_abuse_report": _abuse_report,
    "peer_practice_no_show_report": _no_show_report,
    "partner_spend_alert": _partner_spend_alert,
    "marketplace_session_reminder": _marketplace_session_reminder,
    "inactive_user_engagement": _inactive_user_engagement,
}
