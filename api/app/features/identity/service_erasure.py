"""Erasure by anonymisation: what a closed account becomes 30 days later.

`service_close_account.close_account` only stops sign-in — the row, the
name, the email, every transcript and every mark stay exactly as they were,
because the person closing the account might still be inside the 30-day
retention window the privacy policy promises. This module is the other half:
run on a schedule (`jobs.py`), it finds every account closed more than 30 days
ago and scrubs the personal content off it, while leaving the rows that
payments, `signed_off_by` and memberships point at — a hard delete of the
`users` row would either cascade through those (destroying evidence the
policy promises to keep for 6 years) or be refused by a foreign key, so
erasure keeps the row and empties it instead.

Each other slice's own content is deleted through its own service, not by
this module reaching into its tables directly (`test_slices_call_services_only`
enforces exactly this split).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.settings import Settings, get_settings
from app.features.attempts import service_privacy as attempts_privacy
from app.features.identity import repository
from app.features.peer_practice import service_privacy as peer_practice_privacy
from app.features.tutor_memory import service as tutor_memory_service

log = get_logger(__name__)

# The privacy policy's own number: an account is erased 30 days after it is
# closed, not the moment it is closed, so a person who closes by mistake has a
# month to change their mind before their transcripts are gone for good.
RETENTION_DAYS = 30


async def accounts_due_for_erasure(session: AsyncSession, *, now: datetime) -> list[uuid.UUID]:
    """Every account closed more than 30 days ago that has not yet been erased."""
    cutoff = now - timedelta(days=RETENTION_DAYS)
    return await repository.user_ids_closed_before(session, cutoff=cutoff)


async def _erase_peer_recordings(session: AsyncSession, settings: Settings, user_id: uuid.UUID) -> int:
    """Delete this person's peer-practice recordings, where deleting them does
    not take something away from someone who still has a stake in it.

    A peer session's recording is shared by two people. The rule: delete it
    once both participants are erased, or once this person was its only
    participant (the session names the same user twice); otherwise keep it —
    the other side may still want their copy. There is nothing to scrub short
    of deleting outright: a peer session keeps no per-turn transcript of its
    own (there is no agent in the room to have kept one), only the recording
    itself, so a session that fails this check is left completely untouched.
    """
    sessions = await peer_practice_privacy.sessions_with_recordings_for_user(session, user_id)
    deleted = 0
    for recorded in sessions:
        other_user_id = (
            recorded.patient_user_id if recorded.doctor_user_id == user_id else recorded.doctor_user_id
        )
        only_participant = other_user_id == user_id
        if not only_participant and not await repository.is_erased(session, other_user_id):
            continue
        if await peer_practice_privacy.delete_recording(
            session, settings, recorded.session_id, recorded.recording_key
        ):
            deleted += 1
    return deleted


async def erase_account(session: AsyncSession, user_id: uuid.UUID, *, now: datetime) -> None:
    """Scrub one closed account's personal content.

    Left alone on purpose: the `users` row itself (payments, `signed_off_by`
    result revisions and org memberships all point at it), every attempt row
    (an institution's roster history still needs to know a slot was sat, just
    not what was said in it), and every payment and receipt, which the policy
    keeps for 6 years regardless of what happens to the account.
    """
    scrubbed = await repository.scrub_for_erasure(session, user_id, now=now)
    if not scrubbed:
        # Already gone, or already erased by an earlier, still-running pass —
        # nothing left to do, and nothing else to delete on its behalf either.
        return
    attempts_scrubbed = await attempts_privacy.erase_content_for_user(session, user_id)
    recordings_deleted = await _erase_peer_recordings(session, get_settings(), user_id)
    await tutor_memory_service.forget_everything(session, user_id=user_id, include_debriefs=True)
    log.info(
        "account erased",
        user_id=str(user_id),
        attempts_scrubbed=attempts_scrubbed,
        recordings_deleted=recordings_deleted,
    )


async def erase_due_accounts(session: AsyncSession, *, now: datetime) -> int:
    """Run the job body: erase every account due, and answer how many were."""
    due = await accounts_due_for_erasure(session, now=now)
    for user_id in due:
        await erase_account(session, user_id, now=now)
    return len(due)
