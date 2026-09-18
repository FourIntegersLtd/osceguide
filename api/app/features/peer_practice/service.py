"""Joining the queue, being matched, and practising."""

from __future__ import annotations

import uuid
from datetime import datetime

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
from app.core.ports import VoiceTokens
from app.core.settings import Settings
from app.features.catalog import service as catalog
from app.features.catalog.service import resolve_exam
from app.features.peer_practice import domain, errors, repository
from app.features.peer_practice.models import PracticeSession, QueueEntry
from app.features.peer_practice.schemas import PracticeSessionRead, QueueStatus, RoomGrant
from app.features.voice import service as voice

# What the queue stream reacts to. Named here because this is where it happens.
MATCHED = "practice.matched"


async def join_queue(
    session: AsyncSession, *, user_id: uuid.UUID, exam_code: str, audience: Audience = PUBLIC
) -> QueueStatus:
    """Take a place in the queue, or keep the one you have.

    Joining twice is not an error worth refusing outright — it is somebody
    tapping a button again — so it returns the place they already hold. One
    place per person per exam, whichever room they asked for: asking again for
    a different room returns the place they are already in rather than putting
    them in two queues at once.
    """
    exam = await resolve_exam(session, exam_code)
    ensure_may_address(audience, await audiences_for(session, user_id))
    existing = await repository.live_entry(session, user_id, exam.id)
    # Re-read on a losing race rather than failing: two taps arriving together
    # both found an empty queue, both inserted, and the loser got a 500.
    entry = existing or await repository.join(session, user_id=user_id, exam_id=exam.id, audience=audience)
    if entry is None:
        entry = await repository.live_entry(session, user_id, exam.id)
    if entry is None:
        raise errors.QueueEntryNotFound()
    return await _status(session, entry)


async def read_status(session: AsyncSession, entry_id: uuid.UUID, *, user_id: uuid.UUID) -> QueueStatus:
    entry = await repository.entry_by_id(session, entry_id)
    if entry is None or entry.user_id != user_id:
        raise errors.QueueEntryNotFound()
    return await _status(session, entry)


async def leave_queue(
    session: AsyncSession, entry_id: uuid.UUID, *, user_id: uuid.UUID, now: datetime
) -> None:
    entry = await repository.entry_by_id(session, entry_id)
    if entry is None or entry.user_id != user_id:
        raise errors.QueueEntryNotFound()
    if not await repository.leave(session, entry_id, at=now):
        # Already matched, or already left. Saying "you have left" would be a
        # lie to somebody the matcher has just put into a session.
        raise errors.QueueEntryNotFound()


async def match_waiting(
    session: AsyncSession, exam_id: uuid.UUID, *, audience: Audience = PUBLIC
) -> PracticeSession | None:
    """Pair the next two people who can practise together, inside one room.

    The queue rows are locked while this runs, so two matchers pair different
    people rather than both pairing the same two. Rooms are matched separately:
    somebody waiting in their institution's queue is never paired with a
    stranger from the public pool.
    """
    entries = await repository.claim_waiting(session, exam_id, audience=audience)
    if len(entries) < 2:
        return None

    waiting: list[domain.Waiting] = []
    by_user: dict[str, QueueEntry] = {}
    for entry in entries:
        history = await repository.history_for(session, entry.user_id)
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
    practice = await repository.create_session(
        session, exam_id=exam_id, doctor_user_id=doctor_id, patient_user_id=patient_id
    )
    await repository.set_room(session, practice.id, room_name=f"practice_{practice.id}")
    await repository.mark_matched(
        session,
        [by_user[pair.doctor].id, by_user[pair.patient].id],
        session_id=practice.id,
    )
    # Recorded now rather than at the end, so somebody who abandons a session
    # still does not get the same part twice running.
    await repository.record_role(session, doctor_id, role=str(domain.Role.DOCTOR))
    await repository.record_role(session, patient_id, role=str(domain.Role.PATIENT))

    # Both halves of the pair are told, once the pairing has committed. The
    # matcher is a job rather than a request, and `job_session` flushes what it
    # queued the same way `get_session` does.
    for waiting_user in (doctor_id, patient_id):
        publish_after_commit(session, user_topic(waiting_user), MATCHED)

    return await repository.session_by_id(session, practice.id)


async def read_session(
    session: AsyncSession, session_id: uuid.UUID, *, user_id: uuid.UUID
) -> PracticeSessionRead:
    row = await repository.session_by_id(session, session_id)
    if row is None or user_id not in {row.doctor_user_id, row.patient_user_id}:
        # 404 rather than 403: a session id is not something a stranger should
        # be able to confirm exists.
        raise errors.SessionNotFound()
    return await _session_read(session, row, viewer_id=user_id)


async def end_session(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    user_id: uuid.UUID,
    reason: str | None,
    now: datetime,
) -> PracticeSessionRead:
    row = await repository.session_by_id(session, session_id)
    if row is None or user_id not in {row.doctor_user_id, row.patient_user_id}:
        raise errors.SessionNotFound()
    if row.status == "ended":
        raise errors.SessionAlreadyEnded()
    await repository.end_session(session, session_id, at=now, reason=reason)
    refreshed = await repository.session_by_id(session, session_id)
    return await _session_read(session, refreshed, viewer_id=user_id)  # type: ignore[arg-type]


async def list_my_sessions(session: AsyncSession, user_id: uuid.UUID) -> list[PracticeSessionRead]:
    return [
        await _session_read(session, row, viewer_id=user_id)
        for row in await repository.sessions_for_user(session, user_id)
    ]


async def _status(session: AsyncSession, entry: QueueEntry) -> QueueStatus:
    return QueueStatus(
        entry_id=entry.id,
        status=entry.status,
        position=await repository.position_of(session, entry) if entry.status == "waiting" else None,
        waiting_count=await repository.waiting_count(session, entry.exam_id, audience=audience_of(entry)),
        session_id=entry.matched_session_id,
        audience=AudienceOut.of(entry),
    )


async def _session_read(
    session: AsyncSession, row: PracticeSession, *, viewer_id: uuid.UUID
) -> PracticeSessionRead:
    code = await catalog.exam_code_by_id(session, row.exam_id)
    is_doctor = row.doctor_user_id == viewer_id
    return PracticeSessionRead(
        id=row.id,
        exam_code=code or "",
        my_role=str(domain.Role.DOCTOR if is_doctor else domain.Role.PATIENT),
        partner_user_id=row.patient_user_id if is_doctor else row.doctor_user_id,
        room_name=row.room_name,
        status=row.status,
        started_at=row.started_at,
        ended_at=row.ended_at,
    )


def get_voice_tokens() -> VoiceTokens:
    """The LiveKit adapter, as a FastAPI dependency.

    Imported inside the function so a test can override the dependency
    without the SDK installed, which is the same reason `assistant` does it.
    """
    from app.features.voice.service import get_voice_tokens as build  # noqa: PLC0415

    return build()


async def voice_grant(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    user_id: uuid.UUID,
    tokens: VoiceTokens,
    settings: Settings,
) -> RoomGrant:
    """A token for the room two people were paired into.

    The pairing is the permission: both the doctor and the patient join the
    same room and both may speak, so there is no observer shape here. A
    stranger gets `practice_session_not_found` rather than a refusal, because
    whether a session exists is not something to confirm to somebody who is
    not in it.

    The room was named when the pair was matched and nothing could mint a
    token for it, so the session existed and could never be held.
    """
    row = await repository.session_by_id(session, session_id)
    if row is None or user_id not in {row.doctor_user_id, row.patient_user_id}:
        raise errors.SessionNotFound()
    if row.status == "ended" or not row.room_name:
        raise errors.SessionAlreadyEnded()
    granted = voice.grant_for_room(
        room=row.room_name,
        identity=str(user_id),
        can_publish=True,
        tokens=tokens,
        settings=settings,
    )
    return RoomGrant(token=granted.token, server_url=granted.server_url, room=granted.room)
