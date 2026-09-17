"""Reading an attempt, and the checks every read shares.

Split from `service.py` along the boundary that matters here: those functions
change what an attempt *is* — creating one, failing one, restarting a slot's —
while these only answer questions about one that exists. The ownership check
and the row-to-schema mapping live here because every read applies them and
`service.py` applies them to what it has just written.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import errors, repository
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
    session: AsyncSession, attempt_id: uuid.UUID, *, requester_id: uuid.UUID, is_admin: bool
) -> TranscriptRead:
    attempt = await _require(session, attempt_id)
    _ensure_visible(attempt, requester_id=requester_id, is_admin=is_admin)
    record = await transcripts.transcript_for(session, attempt_id)
    rows = await transcripts.chunks_for(session, attempt_id)
    return TranscriptRead(
        attempt_id=attempt_id,
        complete=bool(record and record.complete),
        messages=[
            TranscriptMessageRead(role=r.role, message=r.message, seq=r.seq, spoken_at=r.spoken_at)
            for r in rows
        ],
    )


async def read_results(
    session: AsyncSession, attempt_id: uuid.UUID, *, requester_id: uuid.UUID, is_admin: bool
) -> list[AssessmentResultRead]:
    attempt = await _require(session, attempt_id)
    _ensure_visible(attempt, requester_id=requester_id, is_admin=is_admin)
    return [
        AssessmentResultRead(
            framework_id=r.framework_id,
            policy_version=r.policy_version,
            model_used=r.model_used,
            payload=dict(r.payload),
            scored_at=r.scored_at,
        )
        for r in await transcripts.results_for(session, attempt_id)
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
    """An attempt, as another slice may see one.

    Not the mapped row: those stay inside this slice. `voice` needs to know
    whose attempt it is and whether it is still joinable; a dashboard needs the
    same plus whether it has been marked.
    """

    id: uuid.UUID
    kind: str
    status: str
    user_id: uuid.UUID
    exam_id: uuid.UUID
    room_name: str | None
    created_at: datetime
    has_result: bool = False


async def attempt_ref(session: AsyncSession, attempt_id: uuid.UUID) -> AttemptRef | None:
    row = await repository.attempt_by_id(session, attempt_id)
    return None if row is None else _ref(row)


async def recent_for_user(session: AsyncSession, user_id: uuid.UUID, *, limit: int) -> list[AttemptRef]:
    """This person's latest attempts, each already saying whether it was marked.

    The `has_result` flag is answered here rather than by the caller, which
    used to read this slice's results table directly to find out.
    """
    rows, _ = await repository.list_for_user(session, user_id, limit=limit)
    return [_ref(row, has_result=bool(await transcripts.results_for(session, row.id))) for row in rows]


def _ref(row: Attempt, *, has_result: bool = False) -> AttemptRef:
    return AttemptRef(
        id=row.id,
        kind=row.kind,
        status=row.status,
        user_id=row.user_id,
        exam_id=row.exam_id,
        room_name=row.room_name,
        created_at=row.created_at,
        has_result=has_result,
    )


async def live_attempts_for_slots(
    session: AsyncSession, slot_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, AttemptRef]:
    """The live attempt on each slot, keyed by slot.

    What a candidate needs to join their own station: the voice token is
    issued per attempt, the attempt is created by the supervisor's dispatch,
    and until this the portal never told the candidate which one was theirs.
    """
    rows = await repository.live_attempts_for_slots(session, list(slot_ids))
    return {row.slot_id: _ref(row) for row in rows if row.slot_id is not None}


async def slots_with_attempts(session: AsyncSession, slot_ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
    """Which of these slots already have an attempt against them.

    Asked by `sittings` before it rebuilds a circuit's slots: an attempt is a
    recording and a marking, and deleting the slot under one would either take
    it with it or fail on the foreign key at the end of the request.
    """
    return await repository.slots_with_attempts(session, list(slot_ids))
