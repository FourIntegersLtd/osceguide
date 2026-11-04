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
from app.features.results.schemas import ResultAcknowledgement, TraineeResultRead, TraineeStationResult
from app.features.reviews import service_summary as reviews
from app.features.roster import service as roster
from app.features.sittings import service_reads as sittings
from app.features.stations import service_reads as stations

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
    return await _project_result(session, revision_row, user_id)


async def preview_result(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID, trainee_id: uuid.UUID
) -> TraineeResultRead:
    """What this candidate would see of their latest decision, released or not.

    For staff only (the route is institution-admin): the same narrow shape the
    candidate gets, so moderation notes never appear. `released_at` is null until release.
    """
    if await sittings.sitting_ref(session, org_id, sitting_id) is None:
        raise errors.SittingNotFound()
    trainee = await roster.read_trainee(session, org_id, trainee_id)
    revision_row = await repository.latest_revision(session, org_id, sitting_id, trainee_id)
    if revision_row is None:
        raise errors.ResultNotFound()
    return await _project_result(session, revision_row, trainee.user_id)


async def _project_result(
    session: AsyncSession,
    revision_row: CandidateResultRevision,
    user_id: uuid.UUID | None,
) -> TraineeResultRead:
    """Build the candidate-facing view of a revision with no release check: callers decide who may see it."""
    acknowledged_at = None
    assessment_score = None
    station_results: list[TraineeStationResult] = []
    if user_id is not None:
        acknowledged_at = await _acknowledged_at(session, revision_row.id, user_id)
        station_results = await _station_results(session, revision_row, user_id)
        scores = [station.score for station in station_results if station.score is not None]
        assessment_score = round(sum(scores) / len(scores), 1) if scores else None
    return TraineeResultRead(
        sitting_id=revision_row.sitting_id,
        assessment_outcome=revision_row.assessment_outcome,
        rationale=revision_row.rationale,
        released_at=revision_row.released_at,
        acknowledged_at=acknowledged_at,
        assessment_score=assessment_score,
        stations=station_results,
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


async def _station_results(
    session: AsyncSession, revision_row: CandidateResultRevision, user_id: uuid.UUID
) -> list[TraineeStationResult]:
    """This person's stations with each one's score on the scale the cohort ranking uses.

    Asked of the reviews slice rather than recomputed here, so a candidate and
    a course lead cannot be shown two different numbers for the same marking.
    The overall score is the mean of these, and null, not zero, when none is marked.
    """
    slots = await sittings.slots_for_sitting(session, revision_row.org_id, revision_row.sitting_id)
    mine = sorted((slot for slot in slots if slot.trainee_id == user_id), key=lambda slot: slot.slot_index)
    if not mine:
        return []
    outcomes = await reviews.outcomes_for_slots(session, revision_row.org_id, [slot.id for slot in mine])
    titles = await stations.summaries_by_version_id(
        session, revision_row.org_id, [slot.station_version_id for slot in mine]
    )
    return [
        TraineeStationResult(
            slot_id=slot.id,
            station_title=(
                titles[slot.station_version_id].title if slot.station_version_id in titles else None
            ),
            score=outcomes[slot.id].score,
            passed=outcomes[slot.id].passed,
        )
        for slot in mine
    ]


async def released_revision_for_user(
    session: AsyncSession, sitting_id: uuid.UUID, user_id: uuid.UUID
) -> CandidateResultRevision | None:
    """The released revision this signed-in person may see, if there is one.

    A result is keyed by `trainees.id`, but the token carries a `users.id`. A trainee whose
    access the organisation revoked sees nothing of it, as the portal shows none of its sittings (T-13).
    """
    trainee_ids = await roster.trainee_ids_for_user(session, user_id)
    revision = await repository.released_revision(session, sitting_id, trainee_ids)
    if revision is None or await roster.is_revoked(session, revision.org_id, user_id):
        return None
    return revision


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
    # A revoked trainee sees nothing of that org's results (T-13), so its sittings stay sealed.
    revoked = await roster.revoked_org_ids(session, user_id)
    return wanted - await repository.released_sitting_ids(
        session, wanted, trainee_ids, excluding_org_ids=revoked
    )


async def _acknowledged_at(
    session: AsyncSession, revision_id: uuid.UUID, user_id: uuid.UUID
) -> datetime | None:
    """When this person acknowledged this revision, or `None` if they have not yet."""
    event = await repository.event_by_idempotency_key(session, _acknowledgement_key(revision_id, user_id))
    return None if event is None else event.at
