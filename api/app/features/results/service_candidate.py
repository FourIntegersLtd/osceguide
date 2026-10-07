"""The candidate's own side of a result: reading it, and acknowledging it.

A candidate is not inside an organisation, so nothing here takes an `org_id`;
what they may see is decided by the revision being released, not by a role.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.results import errors, repository
from app.features.results.models import CandidateResultRevision
from app.features.results.schemas import ResultAcknowledgement, TraineeResultRead
from app.features.reviews import service_summary as reviews
from app.features.roster import service as roster
from app.features.sittings import service_reads as sittings

ACKNOWLEDGED = "acknowledged"


def _acknowledgement_key(revision_id: uuid.UUID, user_id: uuid.UUID) -> str:
    """One acknowledgement per person per revision.

    Keyed on the revision rather than the sitting: a result superseded and
    released again is a different decision, unseen even if the last one was.
    """
    return f"ack:{revision_id}:{user_id}"


async def read_my_result(
    session: AsyncSession, sitting_id: uuid.UUID, user_id: uuid.UUID
) -> TraineeResultRead | None:
    """What the candidate sees: released revisions only, and less of it. `None` until one is released.

    Moderation notes and the evidence snapshot stay internal.
    """
    revision_row = await released_revision_for_user(session, sitting_id, user_id)
    if revision_row is None:
        return None
    return await project_released_result(session, revision_row, user_id)


async def require_released_revision(
    session: AsyncSession, sitting_id: uuid.UUID, user_id: uuid.UUID
) -> CandidateResultRevision:
    """The candidate's released revision, or `result_not_released`: for the writes
    and downloads that have nothing to answer before a release."""
    revision_row = await released_revision_for_user(session, sitting_id, user_id)
    if revision_row is None:
        raise errors.NotReleased()
    return revision_row


async def project_released_result(
    session: AsyncSession,
    revision_row: CandidateResultRevision,
    user_id: uuid.UUID | None,
) -> TraineeResultRead:
    """The fields a candidate may see of one revision.

    Moderation notes and the evidence snapshot stay off this shape. A revision
    that has not been released is refused here, so a draft cannot be rendered
    by handing it in.
    """
    if revision_row.workflow_state != "released":
        raise errors.NotReleased()
    acknowledged_at = None
    assessment_score = None
    if user_id is not None:
        acknowledged_at = await _acknowledged_at(session, revision_row.id, user_id)
        assessment_score = await _assessment_score(session, revision_row, user_id)
    return TraineeResultRead(
        sitting_id=revision_row.sitting_id,
        assessment_outcome=revision_row.assessment_outcome,
        rationale=revision_row.rationale,
        released_at=revision_row.released_at,
        acknowledged_at=acknowledged_at,
        assessment_score=assessment_score,
    )


async def acknowledge_my_result(
    session: AsyncSession, sitting_id: uuid.UUID, user_id: uuid.UUID
) -> ResultAcknowledgement:
    """Record that the candidate has read their released result.

    Written as an event rather than a flag on the revision, which is immutable
    by trigger. Repeating the request returns the first answer rather than
    failing on the unique index.
    """
    revision = await require_released_revision(session, sitting_id, user_id)
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


async def _assessment_score(
    session: AsyncSession, revision_row: CandidateResultRevision, user_id: uuid.UUID
) -> float | None:
    """This person's mean station score, on the scale the cohort ranking uses.

    Asked of the reviews slice rather than recomputed here, so a candidate and
    a course lead cannot be shown two different numbers for the same marking.
    Returns None, not zero, when nothing of theirs has been marked.
    """
    slots = await sittings.slots_for_sitting(session, revision_row.org_id, revision_row.sitting_id)
    mine = [slot.id for slot in slots if slot.trainee_id == user_id]
    if not mine:
        return None
    outcomes = await reviews.outcomes_for_slots(session, revision_row.org_id, mine)
    marked = [outcome.score for outcome in outcomes.values() if outcome.score is not None]
    if not marked:
        return None
    return round(sum(marked) / len(marked), 1)


async def released_revision_for_user(
    session: AsyncSession, sitting_id: uuid.UUID, user_id: uuid.UUID
) -> CandidateResultRevision | None:
    """The released revision this signed-in person may see, if there is one.

    A result is keyed by `trainees.id`, but the token carries a `users.id`.
    """
    trainee_ids = await roster.trainee_ids_for_user(session, user_id)
    return await repository.released_revision(session, sitting_id, trainee_ids)


async def sealed_sittings(
    session: AsyncSession, sitting_ids: Collection[uuid.UUID], user_id: uuid.UUID
) -> set[uuid.UUID]:
    """Which of these sittings have no result released to this person yet, in one query.

    One rule for "sealed until release" (R-1): the attempts slice refuses an exam slot's
    transcript and marks with it, and the trainee portal links no attempt with it.
    """
    wanted = set(sitting_ids)
    if not wanted:
        return set()
    trainee_ids = await roster.trainee_ids_for_user(session, user_id)
    return wanted - await repository.released_sitting_ids(session, wanted, trainee_ids)


async def _acknowledged_at(
    session: AsyncSession, revision_id: uuid.UUID, user_id: uuid.UUID
) -> datetime | None:
    """When this person acknowledged this revision, or `None` if they have not yet."""
    event = await repository.event_by_idempotency_key(session, _acknowledgement_key(revision_id, user_id))
    return None if event is None else event.at
