"""Accepting or declining a match, and what happens to the accept window when nobody answers.

Being paired by `service.match_waiting` does not put two people straight into
a room together: each is asked to accept first, inside `ACCEPT_WINDOW_SECONDS`
(`service.py`). This module is the other half of that handshake — the two
routes it drives, and the lazy timeout check that `read_session` and
`touch_presence` run before anything else, the same way `advance_phases_if_due`
is checked lazily rather than on a clock of its own.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import PUBLIC, audience_of
from app.core.events import publish_after_commit, user_topic
from app.features.attempts import service as attempts
from app.features.peer_practice import errors, repository, repository_sessions
from app.features.peer_practice.models import PracticeSession
from app.features.peer_practice.schemas import PracticeSessionRead
from app.features.peer_practice.service_lifecycle import SESSION_UPDATED
from app.features.peer_practice.service_station import session_read as _session_read

# Re-published so a waiting client's stream is nudged the moment both sides
# have accepted and the session becomes joinable.
ACCEPTED = "practice.accepted"
# The queue keeps a fresh place open this long — the same window `join_queue`
# hands out, so a requeued person is treated exactly like someone joining new.
REQUEUE_WAIT_MINUTES = 10


async def expire_if_due(
    session: AsyncSession, practice_session: PracticeSession, *, now: datetime
) -> PracticeSession:
    """End a pairing whose accept window has closed with nobody left to answer.

    A no-op for anything not still `pending_accept`, or not yet past its
    `accept_expires_at` — the common case, checked on every read so a session
    nobody is watching still resolves itself the next time somebody looks.
    """
    if practice_session.status != "pending_accept" or practice_session.accept_expires_at is None:
        return practice_session
    if now < practice_session.accept_expires_at:
        return practice_session
    await repository_sessions.end_session(session, practice_session.id, at=now, reason="no_response")
    await _requeue_the_still_interested(session, practice_session, exclude_user_id=None, now=now)
    refreshed = await repository_sessions.session_by_id(session, practice_session.id)
    assert refreshed is not None
    # Whoever isn't the one reading right now (a partner sitting on the
    # session screen) learns the window closed without having to ask again.
    for participant in (practice_session.doctor_user_id, practice_session.patient_user_id):
        publish_after_commit(
            session, user_topic(participant), SESSION_UPDATED, {"session_id": str(refreshed.id)}
        )
    return refreshed


async def accept_match(
    session: AsyncSession, session_id: uuid.UUID, *, user_id: uuid.UUID, now: datetime
) -> PracticeSessionRead:
    """Record that this caller accepts a pending pairing, joining the pair once both have.

    Accepting a pairing that has already resolved the other way — declined,
    or timed out — is `partner_unavailable` rather than a plain 404: the
    session did exist, and saying so is what tells this side why nothing
    happened when they tapped accept. Accepting one already fully accepted is
    not an error: the second caller through just sees the settled state.

    A trial whose window has closed cannot accept (the queue entry may have been made
    on its last day). If the partner's window closed while they waited, the pairing ends
    instead of making a room they could not enter, and whoever accepted is queued again.
    """
    practice_session = await _owned_session(session, session_id, user_id=user_id)
    practice_session = await expire_if_due(session, practice_session, now=now)
    if practice_session.status == "ended":
        raise errors.PartnerUnavailableError()
    if practice_session.status == "pending_accept":
        await attempts.require_entitlement(
            session, user_id=user_id, exam_id=practice_session.exam_id, now=now, window_only=True
        )
        column = "doctor_accepted_at" if practice_session.doctor_user_id == user_id else "patient_accepted_at"
        if getattr(practice_session, column) is None:
            await repository_sessions.record_accept(session, session_id, column=column, at=now)
            refreshed = await repository_sessions.session_by_id(session, session_id)
            assert refreshed is not None
            practice_session = refreshed
        both_accepted = (
            practice_session.doctor_accepted_at is not None
            and practice_session.patient_accepted_at is not None
        )
        partner_id = (
            practice_session.patient_user_id
            if practice_session.doctor_user_id == user_id
            else practice_session.doctor_user_id
        )
        if both_accepted and not await attempts.window_is_open(
            session, user_id=partner_id, exam_id=practice_session.exam_id, now=now
        ):
            await repository_sessions.end_session(session, session_id, at=now, reason="partner_unavailable")
            await _requeue_the_still_interested(
                session, practice_session, exclude_user_id=partner_id, now=now
            )
            practice_session = (
                await repository_sessions.session_by_id(session, session_id) or practice_session
            )
            publish_after_commit(
                session, user_topic(partner_id), SESSION_UPDATED, {"session_id": str(session_id)}
            )
            return await _session_read(session, practice_session, viewer_id=user_id)
        if both_accepted:
            await repository_sessions.advance_phase(
                session, session_id, values={"status": "matched", "accept_expires_at": None}
            )
            refreshed = await repository_sessions.session_by_id(session, session_id)
            assert refreshed is not None
            practice_session = refreshed
            for participant in (practice_session.doctor_user_id, practice_session.patient_user_id):
                publish_after_commit(
                    session, user_topic(participant), ACCEPTED, {"session_id": str(session_id)}
                )
    return await _session_read(session, practice_session, viewer_id=user_id)


async def decline_match(
    session: AsyncSession, session_id: uuid.UUID, *, user_id: uuid.UUID, now: datetime
) -> PracticeSessionRead:
    """Refuse a pending pairing, ending it and putting an already-accepting partner back in the queue.

    Only meaningful while the pairing is still `pending_accept` — once both
    sides have accepted there is a session to leave, not a match to decline,
    which is what `end_session` is for.
    """
    practice_session = await _owned_session(session, session_id, user_id=user_id)
    practice_session = await expire_if_due(session, practice_session, now=now)
    if practice_session.status == "ended":
        raise errors.PartnerUnavailableError()
    if practice_session.status != "pending_accept":
        raise errors.SessionAlreadyEnded("Both sides have already accepted this match.")
    await repository_sessions.end_session(session, session_id, at=now, reason="declined")
    await _requeue_the_still_interested(session, practice_session, exclude_user_id=user_id, now=now)
    refreshed = await repository_sessions.session_by_id(session, session_id)
    assert refreshed is not None
    # The partner is still waiting on the pending-accept screen; this event
    # is how they learn the match fell through.
    for participant in (practice_session.doctor_user_id, practice_session.patient_user_id):
        publish_after_commit(
            session, user_topic(participant), SESSION_UPDATED, {"session_id": str(session_id)}
        )
    return await _session_read(session, refreshed, viewer_id=user_id)


async def _owned_session(
    session: AsyncSession, session_id: uuid.UUID, *, user_id: uuid.UUID
) -> PracticeSession:
    """This caller's own session, or `SessionNotFound` for anyone else's or a session that never existed."""
    practice_session = await repository_sessions.session_by_id(session, session_id)
    if practice_session is None or user_id not in {
        practice_session.doctor_user_id,
        practice_session.patient_user_id,
    }:
        raise errors.SessionNotFound()
    return practice_session


async def _requeue_the_still_interested(
    session: AsyncSession,
    practice_session: PracticeSession,
    *,
    exclude_user_id: uuid.UUID | None,
    now: datetime,
) -> None:
    """Put back in the queue whichever side had already accepted before the pairing ended.

    Skipped for `exclude_user_id` — the person who declined is not put back
    into a queue they just chose to leave. A timeout excludes nobody, since
    neither side caused it. Whoever accepted goes back into the same room
    (public, their institution's, or one teaching group) their original queue
    entry addressed, read back from it rather than guessed at.
    """
    from app.features.peer_practice.jobs import enqueue_try_match

    matched_entries = await repository.entries_matched_to(session, practice_session.id)
    entries_by_user = {entry.user_id: entry for entry in matched_entries}
    for candidate_id, accepted_at in (
        (practice_session.doctor_user_id, practice_session.doctor_accepted_at),
        (practice_session.patient_user_id, practice_session.patient_accepted_at),
    ):
        if accepted_at is None or candidate_id == exclude_user_id:
            continue
        original_entry = entries_by_user.get(candidate_id)
        audience = audience_of(original_entry) if original_entry is not None else PUBLIC
        expires_at = now + timedelta(minutes=REQUEUE_WAIT_MINUTES)
        new_entry = await repository.join(
            session,
            user_id=candidate_id,
            exam_id=practice_session.exam_id,
            audience=audience,
            expires_at=expires_at,
        )
        if new_entry is not None:
            await enqueue_try_match(session, exam_id=practice_session.exam_id, audience=audience)
