"""The "come try a station" nudge for someone who signed up and never practised.

Ported from legacy `b2c-api`'s `InactiveUserEngagementService`, which polled
Firestore every 24 hours across all four `APP_TYPES` and sent through
`EmailService.send_inactive_user_engagement_email`. Here it is a single daily
Procrastinate task (`jobs.py`) against the one `users` table, gated by
`settings.engagement_email_enabled` so it cannot fire until the owner turns it
on: see `docs/ENVIRONMENT.md`, `ENGAGEMENT_EMAIL_ENABLED`.

Legacy's selection rules, ported exactly:
- signed up within the lookback window (28 days, `LOOKBACK_DAYS` below,
  matching legacy's `INACTIVE_USER_ENGAGEMENT_LOOKBACK_DAYS`);
- never completed a station (`user_has_completed_station`);
- never sent this email before (`inactive_engagement_email_sent_at` unset);
- not a deleted account (`_should_send_engagement_email`'s `is_deleted` check).

One rule has no legacy equivalent and is new to this port: a consumer account
only, never someone who only exists here as an institution-provisioned
trainee. Legacy's Firestore users were consumer accounts by construction —
b2b's roster lived in a different collection entirely — but the unified
`users` table now holds both, so this slice asks `roster` whether the
candidate has any trainee row at all and skips them if so.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.features.attempts import service_reads as attempts_reads
from app.features.identity import repository
from app.features.notifications import service as notifications
from app.features.roster import service as roster

log = get_logger(__name__)

# Legacy's own number (`product_email_utils.INACTIVE_USER_ENGAGEMENT_LOOKBACK_DAYS`):
# a rolling 28-day window from sign-up, so the nudge always lands while the
# account is still new enough for "try your first station" to make sense.
LOOKBACK_DAYS = 28


async def _is_eligible(session: AsyncSession, user_id: uuid.UUID) -> bool:
    """The two checks that need another slice's data, run after the cheap,
    identity-only filters in `repository.candidates_for_engagement_email`.

    Both are exclusions: a person who has ever finished a station, or who is
    linked to an organisation as a trainee, is never sent this email, however
    long ago they signed up.
    """
    if await attempts_reads.has_completed_any(session, user_id):
        return False
    trainee_ids = await roster.trainee_ids_for_user(session, user_id)
    return len(trainee_ids) == 0


async def send_due_engagement_emails(session: AsyncSession, *, now: datetime) -> int:
    """Queue the engagement email for every eligible account, and answer how
    many were sent.

    Called from `jobs.py` on a daily schedule; also callable directly from a
    test, against a real database, with no queue involved. Each candidate is
    claimed one at a time (`repository.claim_engagement_email`) rather than
    in the same statement that selected them, because eligibility depends on
    `attempts` and `roster`, which the selecting query cannot see — the claim
    is still atomic per account, so two overlapping runs can never both send
    the same person's email.
    """
    window_start = now - timedelta(days=LOOKBACK_DAYS)
    candidates = await repository.candidates_for_engagement_email(
        session, window_start=window_start, window_end=now
    )
    sent = 0
    for candidate in candidates:
        if not await _is_eligible(session, candidate.id):
            continue
        if not await repository.claim_engagement_email(session, candidate.id, now=now):
            # Already sent by an earlier or overlapping run: nothing to do.
            continue
        exam_name = (candidate.exam_code or "SCA").upper()
        await notifications.enqueue_email(
            session,
            recipient=candidate.email,
            subject=f"OSCE Guide - Ready to complete your first {exam_name} station?",
            template_key="inactive_user_engagement",
            payload={
                "display_name": candidate.name or candidate.email.split("@", 1)[0],
                "exam_name": exam_name,
            },
            # One key per account: even if this ran twice for the same
            # person (it cannot — the claim above already prevents it — but
            # a future caller might), the outbox itself refuses a repeat.
            idempotency_key=f"inactive-engagement-{candidate.id}",
        )
        sent += 1
        log.info("engagement email queued", user_id=str(candidate.id))
    return sent
