"""The candidate's own side of a result: reading it, and saying so.

Split from `service.py` along the actor. That module is the organisation's
workflow — draft, sign off, release — and every function in it takes an
`org_id`. Nothing here does: a candidate is not inside an organisation when
they open the email, and what they may see is decided by the revision being
released, not by a role.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.results import errors, repository
from app.features.results.models import CandidateResultRevision
from app.features.results.schemas import ResultAcknowledgement, TraineeResultRead
from app.features.roster import service as roster

ACKNOWLEDGED = "acknowledged"


def _acknowledgement_key(revision_id: uuid.UUID, user_id: uuid.UUID) -> str:
    """One acknowledgement per person per revision.

    Keyed on the revision rather than the sitting: a result that is superseded
    and released again is a different decision, and a candidate has not seen it
    because they saw the last one.
    """
    return f"ack:{revision_id}:{user_id}"


async def read_my_result(
    session: AsyncSession, sitting_id: uuid.UUID, user_id: uuid.UUID
) -> TraineeResultRead:
    """What the candidate sees: released revisions only, and less of it.

    Moderation notes and the evidence snapshot stay internal. b2b's own schema
    doc says not to reproduce disclosure policy in frontend transforms, so the
    narrowing happens here.
    """
    row = await _released_for(session, sitting_id, user_id)
    return TraineeResultRead(
        sitting_id=row.sitting_id,
        assessment_outcome=row.assessment_outcome,
        rationale=row.rationale,
        released_at=row.released_at,
        acknowledged_at=await _acknowledged_at(session, row.id, user_id),
    )


async def acknowledge_my_result(
    session: AsyncSession, sitting_id: uuid.UUID, user_id: uuid.UUID
) -> ResultAcknowledgement:
    """Record that the candidate has read their released result.

    Written as an event on the append-only chain rather than a flag on the
    revision, because the revision is immutable by trigger and because "when
    did they see it" is exactly the kind of question this record exists to
    answer months later. Repeating the request returns the first answer instead
    of failing on the unique index.
    """
    revision = await _released_for(session, sitting_id, user_id)
    key = _acknowledgement_key(revision.id, user_id)

    existing = await repository.event_by_idempotency_key(session, key)
    if existing is not None:
        return ResultAcknowledgement(sitting_id=sitting_id, acknowledged_at=existing.at)

    event = await repository.append_event(
        session,
        revision_id=revision.id,
        event_type=ACKNOWLEDGED,
        actor_user_id=user_id,
        idempotency_key=key,
    )
    return ResultAcknowledgement(sitting_id=sitting_id, acknowledged_at=event.at)


async def _released_for(
    session: AsyncSession, sitting_id: uuid.UUID, user_id: uuid.UUID
) -> CandidateResultRevision:
    """The released revision this signed-in person may see, or a refusal.

    The person is translated into the roster entries they are: a result is
    keyed by `trainees.id` and a token carries a `users.id`.
    """
    trainee_ids = await roster.trainee_ids_for_user(session, user_id)
    row = await repository.released_revision(session, sitting_id, trainee_ids)
    if row is None:
        raise errors.NotReleased()
    return row


async def _acknowledged_at(
    session: AsyncSession, revision_id: uuid.UUID, user_id: uuid.UUID
) -> datetime | None:
    event = await repository.event_by_idempotency_key(session, _acknowledgement_key(revision_id, user_id))
    return None if event is None else event.at
