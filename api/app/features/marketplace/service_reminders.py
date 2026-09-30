"""Emailing both participants of a peer session before it starts.

Ported from legacy `b2c-api`'s `marketplace_reminder_service.py`, which polled
Firestore on a dynamic sleep and sent through `EmailService` directly. Here
the schedule is a Procrastinate periodic task (`jobs.py`) and the send is a
row in the notifications outbox (`notifications.service.enqueue_email`) —
queued in the same transaction that claims the session, so a reminder that
never leaves the outbox because the process died mid-send still leaves a
queued row behind rather than silently vanishing.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.features.catalog import service as catalog
from app.features.identity import service as identity
from app.features.marketplace import repository
from app.features.marketplace.models import PeerSession
from app.features.marketplace.service_reads import peer_username
from app.features.notifications import service as notifications

log = get_logger(__name__)

# Legacy sent the reminder one hour before the session; a session is picked up
# for a reminder once it falls inside that window.
REMINDER_LEAD_TIME = timedelta(hours=1)


async def _queue_reminder(
    session: AsyncSession,
    *,
    peer_session: PeerSession,
    recipient: identity.UserRef,
    partner: identity.UserRef,
    exam_code: str | None,
) -> None:
    """Queue one participant's copy of the reminder, unless their account is closed.

    A closed account is skipped rather than failing the whole session: the
    other participant, if still active, should still be told their partner may
    not show up rather than getting no warning at all.
    """
    status = await identity.account_status(session, recipient.id)
    if status == "deleted":
        return
    await notifications.enqueue_email(
        session,
        recipient=recipient.email,
        subject="OSCE Guide - Practice session reminder",
        template_key="marketplace_session_reminder",
        payload={
            "username": recipient.name or recipient.email.split("@", 1)[0],
            "partner_username": peer_username(partner),
            "scheduled_at": peer_session.starts_at.isoformat(),
            "exam_code": exam_code or "",
            "peer_session_id": str(peer_session.id),
        },
        # One key per session per recipient: a session claimed twice by a
        # retried job run (it cannot be — `claim_due_reminders` already makes
        # that impossible — but a future caller might) still only ever queues
        # one email per person for it.
        idempotency_key=f"marketplace-reminder-{peer_session.id}-{recipient.id}",
    )


async def send_due_reminders(session: AsyncSession, *, now: datetime) -> int:
    """Queue the "starts in an hour" reminder for every session newly due it.

    Returns how many sessions were claimed (0, 1 or 2 emails queued per
    session, depending on whether either participant's account is closed).
    Called from `jobs.py` on a five-minute schedule; also callable directly
    from a test, against a real database, with no queue involved.
    """
    due = await repository.claim_due_reminders(session, now=now, remind_before=now + REMINDER_LEAD_TIME)
    for peer_session in due:
        owner = await identity.user_ref_by_id(session, peer_session.owner_user_id)
        claimer = await identity.user_ref_by_id(session, peer_session.claimer_user_id)
        if owner is None or claimer is None:
            # Should not happen in practice — both ids are `ondelete="CASCADE"`
            # foreign keys to `users`, so a session cannot outlive either
            # participant — but a missing person is a reason to skip this
            # session's emails, not to crash the run for every other session
            # still waiting to be claimed. The session stays claimed either
            # way: retrying it would not find a participant next time either.
            log.warning("marketplace session missing a participant", peer_session_id=str(peer_session.id))
            continue
        exam_code = await catalog.exam_code_by_id(session, peer_session.exam_id)
        await _queue_reminder(
            session, peer_session=peer_session, recipient=owner, partner=claimer, exam_code=exam_code
        )
        await _queue_reminder(
            session, peer_session=peer_session, recipient=claimer, partner=owner, exam_code=exam_code
        )
        log.info("marketplace session reminder queued", peer_session_id=str(peer_session.id))
    return len(due)
