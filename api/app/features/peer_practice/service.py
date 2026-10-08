"""Joining the queue, being matched, and practising."""

from __future__ import annotations

import contextlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import (
    PUBLIC,
    Audience,
    AudienceOut,
    audience_of,
    audiences_for,
    ensure_may_address,
)
from app.core.events import publish_after_commit, user_topic
from app.features.attempts import service as attempts
from app.features.catalog import service as catalog
from app.features.catalog.service import resolve_exam
from app.features.peer_practice import (
    domain,
    errors,
    repository,
    repository_sessions,
    service_recording,
)
from app.features.peer_practice.jobs import enqueue_try_match
from app.features.peer_practice.models import PracticeSession, QueueEntry
from app.features.peer_practice.schemas import PracticeSessionRead, QueueStatus
from app.features.peer_practice.service_lifecycle import (
    SESSION_UPDATED,
    advance_phases_if_due,
    record_presence,
)
from app.features.peer_practice.service_match import expire_if_due
from app.features.peer_practice.service_station import session_read as _session_read
from app.features.peer_practice.station_pick import pick_station_version_id
from app.features.stations import service_reads as stations

# What the queue stream reacts to. Named here because this is where it happens.
MATCHED = "practice.matched"
QUEUE_WAIT_MINUTES = 10
# The end reason the client sends for leaving a consultation with over three
# minutes left (platform-web `ABANDONED_REASON`). Such a session is not marked.
ABANDONED_REASON = "abandoned"
# How long a matched pair has to both accept before the pairing times out and
# whoever did answer is put back in the queue.
ACCEPT_WINDOW_SECONDS = 120


async def join_queue(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    exam_code: str,
    now: datetime,
    audience: Audience = PUBLIC,
) -> QueueStatus:
    """Take a place in the queue, or keep the one you have.

    Practising with another person is paid access, gated the same as
    `POST /attempts` (free trial included). Joining twice is not refused as
    an error — it returns the place already held, whichever room was asked
    for, rather than a second place in a different queue.
    """
    exam = await resolve_exam(session, exam_code)
    await attempts.require_entitlement(session, user_id=user_id, exam_id=exam.id, now=now)
    ensure_may_address(audience, await audiences_for(session, user_id))
    existing = await repository.live_entry(session, user_id, exam.id)
    if existing is None and not await stations.published_library_version_ids(session, exam_id=exam.id):
        raise errors.NoStationsForExam()
    # Re-read on a losing race rather than failing: two taps arriving together
    # both found an empty queue, both inserted, and the loser got a 500.
    expires_at = now + timedelta(minutes=QUEUE_WAIT_MINUTES)
    entry = existing or await repository.join(
        session, user_id=user_id, exam_id=exam.id, audience=audience, expires_at=expires_at
    )
    if entry is None:
        entry = await repository.live_entry(session, user_id, exam.id)
    if entry is None:
        raise errors.QueueEntryNotFound()
    if entry.status == "waiting":
        await enqueue_try_match(session, exam_id=exam.id, audience=audience_of(entry))
    return await _status(session, entry)


async def read_status(session: AsyncSession, entry_id: uuid.UUID, *, user_id: uuid.UUID) -> QueueStatus:
    """One caller's own queue entry, refused for anyone else's."""
    entry = await repository.entry_by_id(session, entry_id)
    if entry is None or entry.user_id != user_id:
        raise errors.QueueEntryNotFound()
    return await _status(session, entry)


async def leave_queue(
    session: AsyncSession, entry_id: uuid.UUID, *, user_id: uuid.UUID, now: datetime
) -> None:
    """Give up a queue place. Refused if it was already matched or already left."""
    entry = await repository.entry_by_id(session, entry_id)
    if entry is None or entry.user_id != user_id:
        raise errors.QueueEntryNotFound()
    if not await repository.leave(session, entry_id, at=now):
        # Already matched, or already left. Saying "you have left" would be a
        # lie to somebody the matcher has just put into a session.
        raise errors.QueueEntryNotFound()


async def match_waiting(
    session: AsyncSession, exam_id: uuid.UUID, *, audience: Audience = PUBLIC, now: datetime | None = None
) -> PracticeSession | None:
    """Pair the next two people who can practise together, inside one room.

    The queue rows are locked while this runs, so two matchers pair different
    people rather than both pairing the same two. Rooms are matched separately:
    somebody waiting in their institution's queue is never paired with a
    stranger from the public pool.

    The pair does not land straight in a joinable session: each is asked to
    accept the match, and the new session starts `pending_accept` with
    `ACCEPT_WINDOW_SECONDS` to answer (see `service_match.accept_match`).
    """
    entries = await repository.claim_waiting(session, exam_id, audience=audience)
    if len(entries) < 2:
        return None

    waiting: list[domain.Waiting] = []
    by_user: dict[str, QueueEntry] = {}
    for entry in entries:
        history = await repository_sessions.history_for(session, entry.user_id)
        waiting.append(
            domain.Waiting(
                user_id=str(entry.user_id),
                last_role=domain.Role(history.last_role) if history and history.last_role else None,
                session_count=history.session_count if history else 0,
                never_doctor=history.never_doctor if history else False,
            )
        )
        by_user[str(entry.user_id)] = entry

    pair = domain.next_pair(waiting)
    if pair is None:
        return None

    doctor_id, patient_id = uuid.UUID(pair.doctor), uuid.UUID(pair.patient)
    station_id = await pick_station_version_id(session, exam_id=exam_id, doctor_user_id=doctor_id)
    matched_at = now if now is not None else datetime.now(UTC)
    practice = await repository_sessions.create_session(
        session,
        exam_id=exam_id,
        doctor_user_id=doctor_id,
        patient_user_id=patient_id,
        station_version_id=station_id,
        status="pending_accept",
        accept_expires_at=matched_at + timedelta(seconds=ACCEPT_WINDOW_SECONDS),
    )
    await repository_sessions.set_room(session, practice.id, room_name=f"practice_{practice.id}")
    await repository.mark_matched(
        session,
        [by_user[pair.doctor].id, by_user[pair.patient].id],
        session_id=practice.id,
    )
    # Recorded now rather than at the end, so somebody who abandons a session
    # still does not get the same part twice running.
    await repository_sessions.record_role(session, doctor_id, role=str(domain.Role.DOCTOR))
    await repository_sessions.record_role(session, patient_id, role=str(domain.Role.PATIENT))

    # Both halves of the pair are told, once the pairing has committed. The
    # matcher is a job rather than a request, and `job_session` flushes what it
    # queued the same way `get_session` does.
    for waiting_user in (doctor_id, patient_id):
        publish_after_commit(session, user_topic(waiting_user), MATCHED, {"session_id": str(practice.id)})

    return await repository_sessions.session_by_id(session, practice.id)


async def read_session(
    session: AsyncSession, session_id: uuid.UUID, *, user_id: uuid.UUID, now: datetime | None = None
) -> PracticeSessionRead:
    """One practice session as its doctor or patient sees it, advancing its phase if due."""
    practice_session = await repository_sessions.session_by_id(session, session_id)
    if practice_session is None or user_id not in {
        practice_session.doctor_user_id,
        practice_session.patient_user_id,
    }:
        # 404 rather than 403: a session id is not something a stranger should
        # be able to confirm exists.
        raise errors.SessionNotFound()
    if now is not None:
        practice_session = await expire_if_due(session, practice_session, now=now)
        code = await catalog.exam_code_by_id(session, practice_session.exam_id) or ""
        practice_session = await advance_phases_if_due(session, practice_session, exam_code=code, now=now)
    return await _session_read(session, practice_session, viewer_id=user_id)


async def touch_presence(
    session: AsyncSession, session_id: uuid.UUID, *, user_id: uuid.UUID, now: datetime
) -> PracticeSessionRead:
    """Mark this caller present and drive the session's phase forward if due."""
    practice_session = await repository_sessions.session_by_id(session, session_id)
    if practice_session is None or user_id not in {
        practice_session.doctor_user_id,
        practice_session.patient_user_id,
    }:
        raise errors.SessionNotFound()
    practice_session = await expire_if_due(session, practice_session, now=now)
    if practice_session.status == "ended":
        raise errors.SessionAlreadyEnded()
    if practice_session.status == "pending_accept":
        raise errors.NotYetAcceptedError()
    practice_session = await record_presence(session, practice_session, user_id=user_id, now=now)
    return await _session_read(session, practice_session, viewer_id=user_id)


async def submit_feedback(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    user_id: uuid.UUID,
    would_practice_again: bool,
    rating: int | None = None,
    comment: str | None = None,
) -> PracticeSessionRead:
    """Record one participant's feedback on a session they were part of.

    `would_practice_again` is the one field this always writes; `rating` is
    the star score and may be left out, the same as the legacy form allowed.
    """
    practice_session = await repository_sessions.session_by_id(session, session_id)
    if practice_session is None or user_id not in {
        practice_session.doctor_user_id,
        practice_session.patient_user_id,
    }:
        raise errors.SessionNotFound()
    # Feedback is on a consultation that took place: ended, and started.
    if practice_session.status != "ended" or practice_session.started_at is None:
        raise errors.FeedbackNotOpenError()
    await repository_sessions.record_feedback(
        session, session_id, rating=rating, comment=comment, would_practice_again=would_practice_again
    )
    refreshed = await repository_sessions.session_by_id(session, session_id)
    return await _session_read(session, refreshed, viewer_id=user_id)  # type: ignore[arg-type]


async def end_session(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    user_id: uuid.UUID,
    reason: str | None,
    now: datetime,
) -> PracticeSessionRead:
    """End a session early, recording why, and stop and queue its recording."""
    practice_session = await repository_sessions.session_by_id(session, session_id)
    if practice_session is None or user_id not in {
        practice_session.doctor_user_id,
        practice_session.patient_user_id,
    }:
        raise errors.SessionNotFound()
    if practice_session.status == "ended":
        raise errors.SessionAlreadyEnded()
    if practice_session.status == "pending_accept":
        raise errors.NotYetAcceptedError()
    # Ending early is the common way a consultation finishes — one of the pair
    # presses the button rather than letting the clock run out — so the
    # recording has to be stopped and queued here too, not only on the
    # `consultation -> debrief` transition.
    # An abandoned consultation (left with more than three minutes to go) was
    # told no feedback would be generated, so it is not marked.
    await service_recording.stop_recording_and_queue(
        session, practice_session, now=now, mark=reason != ABANDONED_REASON
    )
    await repository_sessions.end_session(session, session_id, at=now, reason=reason)
    refreshed = await repository_sessions.session_by_id(session, session_id)
    # The partner is still on the session screen; without this they only learn
    # it ended when their own phase clock runs out.
    for participant in (practice_session.doctor_user_id, practice_session.patient_user_id):
        publish_after_commit(
            session, user_topic(participant), SESSION_UPDATED, {"session_id": str(session_id)}
        )
    return await _session_read(session, refreshed, viewer_id=user_id)  # type: ignore[arg-type]


async def end_session_if_still_running(
    session: AsyncSession, session_id: uuid.UUID, *, reason: str, now: datetime
) -> None:
    """End a practice session on another slice's behalf, doing nothing if it is not running.

    For a caller outside this slice that knows a practice session id but is
    not one of its two participants — `marketplace` cancelling a booking
    whose pair had already joined and started a live consultation. Going
    through `end_session` rather than `repository_sessions.end_session`
    directly matters: it is also what stops and queues the recording, and
    skipping that would leave an egress running with nothing to tell it to
    stop. A session that has already ended, or never existed, is left alone;
    the caller is telling this slice "end it if it is still going", not
    asserting that it is.
    """
    practice_session = await repository_sessions.session_by_id(session, session_id)
    if practice_session is None or practice_session.status == "ended":
        return
    with contextlib.suppress(errors.SessionAlreadyEnded):
        await end_session(
            session,
            session_id,
            user_id=practice_session.doctor_user_id,
            reason=reason,
            now=now,
        )


async def list_my_sessions(session: AsyncSession, user_id: uuid.UUID) -> list[PracticeSessionRead]:
    """Every session this person has been matched into, as doctor or patient."""
    return [
        await _session_read(session, practice_session, viewer_id=user_id)
        for practice_session in await repository_sessions.sessions_for_user(session, user_id)
    ]


async def _status(session: AsyncSession, entry: QueueEntry) -> QueueStatus:
    """Build the wire status for one queue entry: position, room size, and where it landed."""
    return QueueStatus(
        entry_id=entry.id,
        status=entry.status,
        position=await repository.position_of(session, entry) if entry.status == "waiting" else None,
        waiting_count=await repository.waiting_count(session, entry.exam_id, audience=audience_of(entry)),
        session_id=entry.matched_session_id,
        audience=AudienceOut.from_row(entry),
    )


async def session_counts_by_station_version(
    session: AsyncSession, station_version_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """How many peer practice sessions used each station version, for an
    author deciding whether a version is safe to throw away."""
    return await repository_sessions.session_counts_by_station_version(session, station_version_ids)
