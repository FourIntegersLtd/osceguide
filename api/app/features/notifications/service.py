"""Queueing and delivering outbound messages."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionOpener, savepoint
from app.core.logging import get_logger
from app.core.ports import EmailDeliveryTimedOut, EmailSender
from app.core.settings import get_settings
from app.features.notifications import domain, repository
from app.features.notifications.models import OutboundMessage

log = get_logger(__name__)

# What a recipient becomes once the person behind it is erased.
ERASED_RECIPIENT = "erased@anonymised.invalid"
# Mail that is sent to an address after its owner was erased: delivered once, then the outbox must
# not keep the address it was the last thing to name.
SCRUB_RECIPIENT_ON_SEND = frozenset({"account_erased"})


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


async def queued_under(session: AsyncSession, idempotency_key: str) -> tuple[str, dict[str, Any]] | None:
    """The template and payload of the message queued under this key, or None if there is none.

    For a slice that stores only a hash of what it emailed (an invitation link) and later needs
    the wording again, such as a reminder.
    """
    message = await repository.by_idempotency_key(session, idempotency_key)
    if message is None:
        return None
    return message.template_key, dict(message.payload or {})


@dataclass(frozen=True)
class _Claimed:
    """A claimed message as plain data, so sending needs no open session or loaded row."""

    id: uuid.UUID
    recipient: str
    subject: str
    template_key: str
    payload: dict[str, Any] | None
    attempts: int


@dataclass(frozen=True)
class _Outcome:
    """What happened to one claimed message: how it ends, and why when it did not send."""

    message: _Claimed
    error: str | None = None
    abandon: bool = False  # retrying cannot help (unknown template)


async def deliver_due(
    open_session: SessionOpener,
    *,
    sender: EmailSender,
    now: datetime,
    limit: int | None = None,
) -> tuple[int, int]:
    """Send whatever is due. Returns (sent, deferred).

    Three steps, so no database connection or lock is held while the provider answers: one
    session claims a batch (`processing`) and commits; the sends run side by side, a few at a time;
    a second session records each outcome. A worker that dies between the steps leaves its claims
    `processing`, and `reclaim_stale` returns them to the queue. Each message is attempted
    independently: one bad address must not stop the rest of the queue.
    """
    settings = get_settings()
    async with open_session() as session:
        reclaimed = await repository.reclaim_stale(session, before=domain.stale_claim_cutoff(now))
        if reclaimed:
            log.warning("reclaimed stranded messages", count=reclaimed)
        claimed = [
            _Claimed(row.id, row.recipient, row.subject, row.template_key, row.payload, row.attempts + 1)
            for row in await repository.claim_due(
                session, now=now, limit=limit or settings.outbox_delivery_batch
            )
        ]
    if not claimed:
        return 0, 0

    slots = asyncio.Semaphore(settings.outbox_send_concurrency)

    async def attempt(message: _Claimed) -> _Outcome:
        """Send one claimed message and say how it went; never raises, so one failure stays one."""
        try:
            html = _render(message.template_key, message.payload)
        except Exception as exc:  # noqa: BLE001 - unknown template or a template that cannot render
            # Retrying cannot help: the code that queued it is wrong. Failed, so the console
            # lists it, rather than a debug-style email to a real person.
            return _Outcome(message, error=str(exc) or type(exc).__name__, abandon=True)
        async with slots:
            try:
                await sender.send(to=message.recipient, subject=message.subject, html=html)
            except EmailDeliveryTimedOut as exc:
                # Never auto-retry: the provider may have accepted the message after we stopped waiting.
                return _Outcome(message, error=str(exc) or type(exc).__name__, abandon=True)
            except Exception as exc:  # noqa: BLE001 - whatever one send raises is that message's retry
                return _Outcome(message, error=str(exc) or type(exc).__name__)
        return _Outcome(message)

    outcomes = await asyncio.gather(*(attempt(message) for message in claimed))

    sent = 0
    deferred = 0
    unrecorded = 0
    async with open_session() as session:
        for outcome in outcomes:
            try:
                # A savepoint per message: one bad write undoes only itself, not the batch's record.
                async with savepoint(session):
                    ended = await _record_outcome(session, outcome, now=now)
            except Exception:  # noqa: BLE001 - the rest of the batch must still be recorded
                # Left `processing`: `reclaim_stale` sends it again, once, rather than all of them.
                log.exception("outbox outcome not recorded", message_id=str(outcome.message.id))
                unrecorded += 1
                continue
            sent += ended == "sent"
            deferred += ended == "retry"
    if unrecorded:
        log.error("outbox outcomes not recorded", count=unrecorded)
    return sent, deferred


async def _record_outcome(session: AsyncSession, outcome: _Outcome, *, now: datetime) -> str:
    """Write how one send ended and say which way: `sent`, `retry` or `failed`."""
    message = outcome.message
    if outcome.error is None:
        await repository.mark_sent(session, message.id, at=now)
        if message.template_key in SCRUB_RECIPIENT_ON_SEND:
            await repository.scrub_recipient(session, message.id, placeholder=ERASED_RECIPIENT)
        return "sent"
    if not outcome.abandon and domain.should_retry(attempts=message.attempts):
        await repository.mark_retry(
            session,
            message.id,
            attempts=message.attempts,
            available_at=domain.next_available(attempts=message.attempts, now=now),
            error=outcome.error,
        )
        return "retry"
    # Abandoned rather than retried forever, so somebody can see that this one needs a person:
    # an error, so it reaches Sentry, and a `failed` row, which the console lists with a retry.
    log.error(
        "message abandoned",
        message_id=str(message.id),
        template_key=message.template_key,
        attempts=message.attempts,
    )
    await repository.mark_failed(session, message.id, attempts=message.attempts, error=outcome.error)
    return "failed"


async def erase_recipients(session: AsyncSession, emails: list[str]) -> None:
    """The people behind these addresses are being erased: queued mail for them is dropped and
    sent mail stops naming them. Compared lower-case, as addresses are stored."""
    await repository.erase_recipients(
        session, {email.lower() for email in emails}, placeholder=ERASED_RECIPIENT
    )


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


def _app_url(path: str) -> str:
    """An absolute address on the web app; `path` starts with a slash."""
    return f"{get_settings().frontend_url.rstrip('/')}{path}"


def _token_link(path: str, escaped_fields: dict[str, str]) -> str:
    """A link to `path` carrying the email's single-use token."""
    return _app_url(f"{path}?token={escaped_fields.get('token', '')}")


def _button(link: str, label: str) -> str:
    """The email's one primary action, the only place the institution colour appears."""
    return (
        f'<p style="margin:24px 0 0"><a href="{link}" style="display:inline-block;background:#090C85;'
        'color:#fff;text-decoration:none;padding:10px 20px;border-radius:10px;font-weight:500"'
        f">{label}</a></p>"
    )


def _page(heading: str, *blocks: str) -> str:
    """An email body: a heading, then its already-escaped paragraphs."""
    return f"<h1>{heading}</h1>" + "".join(blocks)


def _password_reset(escaped_fields: dict[str, str]) -> str:
    """The body for a password-reset email, linking to the reset form with its token."""
    link = _token_link("/reset-password", escaped_fields)
    return _page(
        "Reset your password",
        "<p>Use the link below to choose a new password. It expires in an hour, "
        "and using it signs you out everywhere else.</p>"
        f'<p><a href="{link}">Choose a new password</a></p>'
        "<p>If you did not ask for this, nothing has changed and you can ignore it.</p>",
    )


def _email_change(escaped_fields: dict[str, str]) -> str:
    """The body for the link that confirms a new sign-in address."""
    link = _token_link("/confirm-email", escaped_fields)
    return _page(
        "Confirm your new email address",
        "<p>Use the link below to make this the address you sign in with. It expires in an hour, "
        "and using it signs you out everywhere.</p>"
        f'<p><a href="{link}">Confirm this address</a></p>'
        "<p>If you did not ask for this, nothing has changed and you can ignore it.</p>",
    )


def _email_change_requested(escaped_fields: dict[str, str]) -> str:
    """The body sent to the current address when a change to a new one is asked for."""
    return _page(
        "A change of email was requested",
        "<p>Someone asked to move your OSCE Guide account to "
        f"{escaped_fields.get('new_email', 'a new address')}. Nothing changes until that address "
        "confirms.</p>"
        "<p>If this was not you, reset your password now.</p>",
    )


def _account_reopened(escaped_fields: dict[str, str]) -> str:
    """The body sent to an owner whose closed account came back when they signed in."""
    return _page(
        "Your account is open again",
        "<p>You signed in to your closed OSCE Guide account, so it has been reopened and will not be "
        "erased.</p>"
        "<p>If this was not you, reset your password straight away or contact support.</p>",
    )


def _account_erased(escaped_fields: dict[str, str]) -> str:
    """The body sent to the address an erased account had, once, as the last message to it."""
    return _page(
        "Your account has been erased",
        "<p>Thirty days after you closed your OSCE Guide account, we erased it: your name, email, "
        "photo, sign-in details and the transcripts of your consultations are gone.</p>"
        "<p>Payment records are kept for six years, as our privacy policy says. "
        "This is the last message we will send to this address.</p>",
    )


def _email_changed_notice(escaped_fields: dict[str, str]) -> str:
    """The body sent to the old address once an account has moved to a new one."""
    return _page(
        "Your email address was changed",
        "<p>Your OSCE Guide account now signs in with "
        f"{escaped_fields.get('new_email', 'a new address')}.</p>"
        "<p>If this was not you, reset your password straight away or contact support.</p>",
    )


def _result_released(escaped_fields: dict[str, str]) -> str:
    """The body telling a candidate their sitting's outcome is ready to read."""
    link = _app_url(
        f"/app/{escaped_fields.get('org_slug', '')}/trainee/results/{escaped_fields.get('sitting_id', '')}"
    )
    institution = escaped_fields.get("org_name") or "Your institution"
    return _page(
        "Your result is available",
        f"<p>{institution} has released the outcome for this sitting.</p>"
        f'<p><a href="{link}">Read your result</a></p>',
    )


def _trainee_sitting_link(escaped_fields: dict[str, str]) -> str:
    """Where a trainee opens the sitting an email is about."""
    return _app_url(
        f"/app/{escaped_fields.get('org_slug', '')}/trainee/sittings/{escaped_fields.get('sitting_id', '')}"
    )


def _sitting_scheduled(escaped_fields: dict[str, str]) -> str:
    """The body telling a trainee they have been placed on a dated sitting."""
    when = _in_words(escaped_fields.get("scheduled_at", ""))
    return _page(
        "You are scheduled for a sitting",
        f"<p>{escaped_fields.get('org_name') or 'Your institution'} has scheduled you for "
        f"{escaped_fields.get('sitting_name', 'a sitting')} on {when}.</p>"
        f'<p><a href="{_trainee_sitting_link(escaped_fields)}">Open the sitting</a></p>',
    )


def _exam_day_reminder(escaped_fields: dict[str, str]) -> str:
    """The body sent on the morning of a sitting to everyone on it."""
    when = _in_words(escaped_fields.get("scheduled_at", ""))
    return _page(
        "Your sitting is today",
        f"<p>{escaped_fields.get('sitting_name', 'Your sitting')} with "
        f"{escaped_fields.get('org_name') or 'your institution'} takes place today, {when}.</p>"
        f'<p><a href="{_trainee_sitting_link(escaped_fields)}">Open the sitting</a></p>',
    )


def _review_assigned(escaped_fields: dict[str, str]) -> str:
    """The body telling a supervisor a circuit's reviews are theirs."""
    link = _app_url(
        f"/app/{escaped_fields.get('org_slug', '')}/circuits/{escaped_fields.get('circuit_id', '')}"
    )
    return _page(
        "You are the reviewer for a circuit",
        f"<p>{escaped_fields.get('org_name') or 'Your institution'} has named you as the reviewer for "
        f"{escaped_fields.get('circuit_name', 'a circuit')} in "
        f"{escaped_fields.get('sitting_name', 'a sitting')}.</p>"
        f'<p><a href="{link}">Open the circuit</a></p>',
    )


def _invitation(escaped_fields: dict[str, str]) -> str:
    """The body inviting a new account holder to set a password and sign in."""
    link = _token_link("/accept-invitation", escaped_fields)
    return (
        f'<h1 style="margin:0 0 16px;font-size:22px;font-weight:600">'
        f"You are invited to {escaped_fields.get('invited_to', '')}</h1>"
        f'<p style="{_BODY}">{escaped_fields.get("invited_to", "")} has invited you to OSCE Guide. '
        "Set a password to get started.</p>"
        f"{_button(link, 'Set your password')}"
        f'<p style="{_META}">This link expires in 7 days. Not expecting this? You can ignore this '
        "email and the account stays locked.</p>"
    )


def _invitation_reminder(escaped_fields: dict[str, str]) -> str:
    """The body nudging someone who was invited five days ago and has not set a password.

    Carries a fresh link (the first cannot be repeated). With `exam_title` it says which
    practice access is waiting.
    """
    link = _token_link("/accept-invitation", escaped_fields)
    waiting = (
        f"your practice access to {escaped_fields['exam_title']}"
        if escaped_fields.get("exam_title")
        else "your account"
    )
    return _page(
        f"Your invitation to {escaped_fields.get('invited_to', '')} is still waiting",
        f"<p>{escaped_fields.get('invited_to', '')} invited you to OSCE Guide and {waiting} is not "
        "set up yet. Set a password to get started.</p>"
        f"{_button(link, 'Set your password')}"
        f'<p style="{_META}">This link expires in 7 days. Not expecting this? You can ignore this '
        "email and the account stays locked.</p>",
    )


def _referral_redeemed(escaped_fields: dict[str, str]) -> str:
    """The body telling a referrer that someone bought with their code and what it earned.

    It does not name the buyer: the referrer is told the amount, not who paid.
    """
    link = _app_url("/account")
    return _page(
        "Someone used your referral code",
        f"<p>A purchase with your code earned you {escaped_fields.get('earned', '')}. "
        "It is added to your referral balance.</p>"
        f'<p><a href="{link}">See your referrals</a></p>',
    )


def _practice_access_invitation(escaped_fields: dict[str, str]) -> str:
    """The body inviting someone with no account yet to practise an exam an organisation chose.

    Same token and link as `_invitation`: choosing the password is what accepts it, and the
    practice access is already attached to the account waiting behind the link.
    """
    link = _token_link("/accept-invitation", escaped_fields)
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
    link = _app_url("/app/me")
    return (
        f'<h1 style="margin:0 0 16px;font-size:22px;font-weight:600">'
        f"{escaped_fields.get('granted_by', '')} has given you practice access</h1>"
        f'<p style="{_BODY}">You can now practise <strong>{escaped_fields.get("exam_title", "")}</strong> '
        "with your existing OSCE Guide account. There is nothing new to set up.</p>"
        f"{_button(link, 'Start practising')}"
    )


def _entitlement_expiring(escaped_fields: dict[str, str]) -> str:
    """The body warning that bought access ends soon (S-12)."""
    link = _app_url("/app/me/settings")
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
    link = _app_url("/app/me/settings")
    return _page(
        "Your receipt",
        f"<p>Thank you for your payment of {total}.</p>"
        f"<p>Receipt {escaped_fields.get('receipt_id', '')} — {escaped_fields.get('plan_label', '')}, "
        f"access until {escaped_fields.get('plan_end_date', '')}.</p>"
        f"{_button(link, 'Open your receipts')}",
    )


def _abuse_report(escaped_fields: dict[str, str]) -> str:
    """The body alerting support to a peer-practice abuse report."""
    return _page(
        "Peer-practice abuse report",
        f"<p>Session {escaped_fields.get('session_id', '')}, "
        f"reported by {escaped_fields.get('reporter', '')} "
        f"against {escaped_fields.get('reported', '')}.</p>"
        f"<p>{escaped_fields.get('message', '') or '(no message given)'}</p>",
    )


def _no_show_report(escaped_fields: dict[str, str]) -> str:
    """The body alerting support to a peer-practice no-show report."""
    return _page(
        "Peer-practice no-show report",
        f"<p>Session {escaped_fields.get('session_id', '')}, "
        f"reported by {escaped_fields.get('reporter', '')}.</p>"
        f"<p>{escaped_fields.get('message', '') or '(no message given)'}</p>",
    )


def _partner_spend_alert(escaped_fields: dict[str, str]) -> str:
    """The body telling the team a partner pilot's estimated spend crossed a threshold.

    Oracle: b2c `partner_spend_alert_email.html`, the same figures and the same
    disclaimer, which is what keeps it from being read as the partner's invoice.
    """
    return _page(
        f"{escaped_fields.get('partner', '')} pilot spend alert",
        f"<p>Estimated spend has reached {escaped_fields.get('estimated_spend', '')}, "
        f"past the {escaped_fields.get('threshold', '')} threshold, for "
        f"{escaped_fields.get('from_date', '')} to {escaped_fields.get('to_date', '')}.</p>"
        "<ul>"
        f"<li>Estimated clicks: {escaped_fields.get('estimated_clicks', '')} at "
        f"{escaped_fields.get('cost_per_click', '')} each</li>"
        f"<li>Gross revenue from acquired users: {escaped_fields.get('gross_revenue', '')}</li>"
        f"<li>Net margin: {escaped_fields.get('net_margin', '')}</li>"
        "</ul>"
        f"<p><small>{escaped_fields.get('disclaimer', '')}</small></p>",
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
    link = _app_url(f"/app/me/marketplace/session/{escaped_fields.get('peer_session_id', '')}")
    return _page(
        "Your practice session starts in an hour",
        f"<p>Hi {escaped_fields.get('username', 'there')}, you are practising with "
        f"{escaped_fields.get('partner_username', 'your partner')} at "
        f"{_in_words(escaped_fields.get('scheduled_at', ''))}.</p>"
        f'<p><a href="{link}">Open the session</a></p>',
    )


def _inactive_user_engagement(escaped_fields: dict[str, str]) -> str:
    """The body nudging a signed-up but never-practised person to try their first station.

    `escaped_fields` carries the payload `identity.service_engagement` builds: the
    recipient's display name and the exam their account is set to.
    """
    link = _app_url("/dashboard")
    exam_name = escaped_fields.get("exam_name", "")
    first_station = f"first {exam_name} station" if exam_name else "first station"
    return _page(
        f"Ready to complete your {first_station}?",
        f"<p>Hi {escaped_fields.get('display_name', 'Doctor')}, you signed up but have not yet "
        "run through a practice station. It only takes a few minutes to see how it works.</p>"
        f'<p><a href="{link}">Start your first station</a></p>',
    )


def _organization_contract_ended(escaped_fields: dict[str, str]) -> str:
    """The body telling an organisation's admins its contract ended and access is suspended (S-16)."""
    return _page(
        f"{escaped_fields.get('organization', 'Your organisation')}: contract ended",
        "<p>Your contract ended, so access for your organisation is suspended. Exams that are "
        "already running can finish; nothing new can be started. Contact us to renew and "
        "we will restore access.</p>",
    )


_TEMPLATES: dict[str, Callable[[dict[str, str]], str]] = {
    "organization_contract_ended": _organization_contract_ended,
    "password_reset": _password_reset,
    "email_change": _email_change,
    "email_changed_notice": _email_changed_notice,
    "email_change_requested": _email_change_requested,
    "account_reopened": _account_reopened,
    "account_erased": _account_erased,
    "payment_receipt": _payment_receipt,
    "entitlement_expiring": _entitlement_expiring,
    "invitation": _invitation,
    "sitting_scheduled": _sitting_scheduled,
    "exam_day_reminder": _exam_day_reminder,
    "review_assigned": _review_assigned,
    "invitation_reminder": _invitation_reminder,
    "referral_redeemed": _referral_redeemed,
    "practice_access_invitation": _practice_access_invitation,
    "practice_access_granted": _practice_access_granted,
    "candidate_result_released": _result_released,
    "peer_practice_abuse_report": _abuse_report,
    "peer_practice_no_show_report": _no_show_report,
    "partner_spend_alert": _partner_spend_alert,
    "marketplace_session_reminder": _marketplace_session_reminder,
    "inactive_user_engagement": _inactive_user_engagement,
}
