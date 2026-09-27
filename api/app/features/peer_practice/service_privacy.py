"""What erasure (E-4) does to a peer session's recording.

A peer session's recording belongs to two people, not one — there is no agent
in the room keeping a transcript the way an attempt's patient does, so the
recording is the only record the pair leaves, and either side may still want
it while the other has closed their account. Deciding whether *both* sides
are now erased is `identity.service_erasure`'s job, because a participant's
erased status is identity's own data and this slice may not reach for it
directly (`test_slices_call_services_only` enforces exactly that split). What
belongs here is the mechanical half: telling the caller which of a person's
sessions still hold a recording, and deleting one once the caller has decided
it may go.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import Settings
from app.features.media_production import service_storage as storage
from app.features.peer_practice import repository_sessions


@dataclass(frozen=True)
class RecordedSession:
    """Just enough of one session for `identity.service_erasure` to decide
    whether its recording may be deleted, without handing over the ORM row
    itself (which would be a `.models` import this slice's callers may not make)."""

    session_id: uuid.UUID
    doctor_user_id: uuid.UUID
    patient_user_id: uuid.UUID
    recording_key: str


async def sessions_with_recordings_for_user(
    session: AsyncSession, user_id: uuid.UUID
) -> list[RecordedSession]:
    """Every session this person was part of that still holds a recording key.

    A session whose recording was already deleted (by an earlier pass, or
    because it never recorded at all) has no key and is left out, which is
    what makes calling this twice for the same person idempotent.
    """
    rows = await repository_sessions.sessions_for_user(session, user_id, limit=1000)
    return [
        RecordedSession(
            session_id=row.id,
            doctor_user_id=row.doctor_user_id,
            patient_user_id=row.patient_user_id,
            recording_key=row.recording_key,
        )
        for row in rows
        if row.recording_key
    ]


async def delete_recording(
    session: AsyncSession, settings: Settings, session_id: uuid.UUID, recording_key: str
) -> bool:
    """Delete one session's S3 recording and blank its pointers.

    The object is deleted before the row is written, not after: a crash
    between the two leaves the pointer in place, so the next run's
    `sessions_with_recordings_for_user` still finds it and retries a delete
    that S3 already treats as a no-op — safe to repeat, unlike the reverse
    order, which would leak the object if the row write never happened.
    Answers whether there was anything to do, so a caller that already
    cleared this session (a second pass) can tell it did nothing.
    """
    storage.remove_key(settings, recording_key)
    return await repository_sessions.clear_recording(session, session_id)
