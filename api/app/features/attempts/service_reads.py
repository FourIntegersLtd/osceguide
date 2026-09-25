"""Reading an attempt, and the checks every read shares.

The ownership check and the row-to-schema mapping live here because every read applies them, and
`service.py` applies them to what it has just written.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.attempts import errors, repository, service_access
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.models import Attempt
from app.features.attempts.schemas import (
    AssessmentResultRead,
    AttemptRead,
    TranscriptMessageRead,
    TranscriptRead,
)


async def _require(session: AsyncSession, attempt_id: uuid.UUID) -> Attempt:
    attempt = await repository.attempt_by_id(session, attempt_id)
    if attempt is None:
        raise errors.AttemptNotFound()
    return attempt


async def read_attempt(
    session: AsyncSession, attempt_id: uuid.UUID, *, requester_id: uuid.UUID, is_admin: bool
) -> AttemptRead:
    attempt = await _require(session, attempt_id)
    _ensure_visible(attempt, requester_id=requester_id, is_admin=is_admin)
    return _attempt_read(attempt)


async def read_transcript(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    requester_id: uuid.UUID,
    is_admin: bool,
    memberships: Sequence[Membership] = (),
) -> TranscriptRead:
    """The turns of one consultation.

    Readable by the candidate who spoke them and by the examiner named on the circuit they happened
    in — the widening lives in `service_access`, since the tutor's summaries go through this read too,
    asking as the candidate.
    """
    attempt = await _require(session, attempt_id)
    await service_access.ensure_readable(
        session, attempt, requester_id=requester_id, is_admin=is_admin, memberships=memberships
    )
    record = await transcripts.transcript_for(session, attempt_id)
    turns = await transcripts.chunks_for(session, attempt_id)
    return TranscriptRead(
        attempt_id=attempt_id,
        complete=bool(record and record.complete),
        messages=[
            TranscriptMessageRead(
                role=turn.role, message=turn.message, seq=turn.seq, spoken_at=turn.spoken_at
            )
            for turn in turns
        ],
    )


async def read_results(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    requester_id: uuid.UUID,
    is_admin: bool,
    memberships: Sequence[Membership] = (),
) -> list[AssessmentResultRead]:
    attempt = await _require(session, attempt_id)
    await service_access.ensure_readable(
        session, attempt, requester_id=requester_id, is_admin=is_admin, memberships=memberships
    )
    return [
        AssessmentResultRead(
            framework_id=result.framework_id,
            policy_version=result.policy_version,
            model_used=result.model_used,
            payload=dict(result.payload),
            scored_at=result.scored_at,
        )
        for result in await transcripts.results_for(session, attempt_id)
    ]


def _ensure_visible(attempt: Attempt, *, requester_id: uuid.UUID, is_admin: bool) -> None:
    if attempt.user_id != requester_id and not is_admin:
        raise errors.AttemptNotYours()


def _attempt_read(attempt: Attempt) -> AttemptRead:
    return AttemptRead(
        id=attempt.id,
        kind=attempt.kind,
        status=attempt.status,
        exam_id=attempt.exam_id,
        station_version_id=attempt.station_version_id,
        room_name=attempt.room_name,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        created_at=attempt.created_at,
    )


@dataclass(frozen=True)
class AttemptRef:
    """An attempt, as another feature may see one — not the mapped row, which stays internal.

    `voice` needs to know whose attempt it is and whether it is still joinable; a dashboard needs the
    same plus whether it has been marked; a tutor recalling a consultation needs which station it was
    and when it finished.
    """

    id: uuid.UUID
    kind: str
    status: str
    user_id: uuid.UUID
    exam_id: uuid.UUID
    room_name: str | None
    created_at: datetime
    station_version_id: uuid.UUID | None = None
    completed_at: datetime | None = None
    has_result: bool = False


async def attempt_ref(session: AsyncSession, attempt_id: uuid.UUID) -> AttemptRef | None:
    attempt = await repository.attempt_by_id(session, attempt_id)
    return None if attempt is None else _ref(attempt)


async def recent_for_user(session: AsyncSession, user_id: uuid.UUID, *, limit: int) -> list[AttemptRef]:
    """This person's latest attempts, each already saying whether it was marked."""
    attempts, _ = await repository.list_for_user(session, user_id, limit=limit)
    marked = await transcripts.attempt_ids_with_results(session, [attempt.id for attempt in attempts])
    return [_ref(attempt, has_result=attempt.id in marked) for attempt in attempts]


async def evaluated_for_user(
    session: AsyncSession, user_id: uuid.UUID, *, exam_id: uuid.UUID | None = None, limit: int
) -> list[AttemptRef]:
    """This person's marked attempts, newest first, optionally for one exam.

    The consumer dashboard draws a performance chart from exactly this set; paging `recent_for_user`
    and discarding whatever is unmarked would silently truncate a trend to whatever fell in the page.
    """
    attempts = await repository.evaluated_for_user(session, user_id, exam_id=exam_id, limit=limit)
    return [_ref(attempt, has_result=True) for attempt in attempts]


def _ref(attempt: Attempt, *, has_result: bool = False) -> AttemptRef:
    return AttemptRef(
        id=attempt.id,
        kind=attempt.kind,
        status=attempt.status,
        user_id=attempt.user_id,
        exam_id=attempt.exam_id,
        room_name=attempt.room_name,
        created_at=attempt.created_at,
        station_version_id=attempt.station_version_id,
        completed_at=attempt.completed_at,
        has_result=has_result,
    )


async def live_attempts_for_slots(
    session: AsyncSession, slot_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, AttemptRef]:
    """The live attempt on each slot, keyed by slot.

    What a candidate needs to join their own station: the voice token is issued per attempt, and the
    attempt is created by the supervisor's dispatch.
    """
    attempts = await repository.live_attempts_for_slots(session, list(slot_ids))
    return {attempt.slot_id: _ref(attempt) for attempt in attempts if attempt.slot_id is not None}


async def slots_with_attempts(session: AsyncSession, slot_ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
    """Which of these slots already have an attempt against them.

    Asked by `sittings` before it rebuilds a circuit's slots: an attempt is a
    recording and a marking, and deleting the slot under one would either take
    it with it or fail on the foreign key at the end of the request.
    """
    return await repository.slots_with_attempts(session, list(slot_ids))


async def set_entries_with_attempts(session: AsyncSession, entry_ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
    """Which of these practice-set entries already have an attempt against them.

    The same question `sittings` asks of its slots, asked by `station_sets`
    before a learner throws a set away. The answer cannot be read off the
    entry's own counter, because the console's "reset attempts" zeroes that and
    keeps the recording — the attempt row is the fact.
    """
    return await repository.set_entries_with_attempts(session, list(entry_ids))


async def count_consultations(session: AsyncSession) -> int:
    """Every consultation this platform has run, debriefs excluded."""
    return await repository.count_completed(session)


async def count_debriefs(session: AsyncSession) -> int:
    """Every debrief, which is an attempt of its own kind against another."""
    return await repository.count_completed(session, kind="debrief")


async def count_feedback(session: AsyncSession) -> int:
    """Every attempt that has been marked — the feedback counter."""
    return await repository.count_evaluated(session)
