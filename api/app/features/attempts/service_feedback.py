"""An attempt's marking, read by the rubric it was marked with.

Every screen and dashboard that shows a mark asks here, so a candidate's
feedback, their performance chart and an admin's inspector read one result
by one rubric: the structure and display frozen on the attempt, or, for an
attempt frozen before those were, the rubric `rubrics.scoring_rubric`
resolves for it (its framework's version, else its exam's first version 2
platform rubric for an imported `legacy-b2c` row).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.attempts import domain_definition, errors, repository, service_access
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.models import Attempt
from app.features.attempts.schemas import AttemptFeedbackRead, MarkedResultRead, MarkingRubricRead
from app.features.catalog import service as catalog
from app.features.rubrics import service_marking as rubrics


@dataclass(frozen=True)
class ScoredResult:
    """An attempt's latest result and the rubric that reads it."""

    attempt_id: uuid.UUID
    rubric: rubrics.ScoringRubric
    payload: dict[str, Any]
    scored_at: datetime


async def read_feedback(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    requester_id: uuid.UUID,
    is_admin: bool,
    memberships: Sequence[Membership] = (),
) -> AttemptFeedbackRead:
    """The frozen rubric, its resolved display, and every result with its totals.

    Readable by the same people as the transcript (`service_access.ensure_readable`).
    """
    attempt = await repository.attempt_by_id(session, attempt_id)
    if attempt is None:
        raise errors.AttemptNotFound()
    await service_access.ensure_readable(
        session, attempt, requester_id=requester_id, is_admin=is_admin, memberships=memberships
    )
    scoring_rubric = await _scoring_rubric_for(session, attempt, exam_versions={})
    stored_results = await transcripts.results_for(session, attempt.id)
    return AttemptFeedbackRead(
        attempt_id=attempt.id,
        rubric=MarkingRubricRead(
            version_id=scoring_rubric.version_id,
            structure=scoring_rubric.raw_structure,
            display=scoring_rubric.display,
            rating=rubrics.rating_read(scoring_rubric.structure),
        )
        if scoring_rubric
        else None,
        results=[
            MarkedResultRead(
                framework_id=stored_result.framework_id,
                policy_version=stored_result.policy_version,
                model_used=stored_result.model_used,
                payload=dict(stored_result.payload),
                scored_at=stored_result.scored_at,
                totals=rubrics.totals_read(scoring_rubric, stored_result.payload) if scoring_rubric else None,
            )
            for stored_result in stored_results
        ],
    )


async def latest_scored(session: AsyncSession, attempt_ids: Sequence[uuid.UUID]) -> list[ScoredResult]:
    """Each attempt's latest result with its own rubric, in the order given.

    For a dashboard that has already chosen whose attempts to read: no access
    check here. An attempt with no result, or no rubric to read it by, is
    left out rather than scored against another attempt's rules.
    """
    exam_versions: dict[uuid.UUID, uuid.UUID | None] = {}
    scored: list[ScoredResult] = []
    for attempt_id in attempt_ids:
        attempt = await repository.attempt_by_id(session, attempt_id)
        if attempt is None:
            continue
        stored_results = await transcripts.results_for(session, attempt_id)
        if not stored_results:
            continue
        scoring_rubric = await _scoring_rubric_for(session, attempt, exam_versions=exam_versions)
        if scoring_rubric is None:
            continue
        latest = stored_results[-1]
        scored.append(
            ScoredResult(
                attempt_id=attempt_id,
                rubric=scoring_rubric,
                payload=dict(latest.payload),
                scored_at=latest.scored_at,
            )
        )
    return scored


async def _scoring_rubric_for(
    session: AsyncSession, attempt: Attempt, *, exam_versions: dict[uuid.UUID, uuid.UUID | None]
) -> rubrics.ScoringRubric | None:
    """The rubric this attempt is read by. `exam_versions` caches each exam's rubric version."""
    snapshot = domain_definition.rubric_for(attempt.definition)
    frozen = rubrics.frozen_scoring_rubric(snapshot)
    if frozen is not None:
        return frozen
    if attempt.exam_id not in exam_versions:
        exam = await catalog.exam_for_attempt(session, attempt.exam_id)
        exam_versions[attempt.exam_id] = exam.rubric_version_id
    return await rubrics.scoring_rubric(
        session, snapshot, exam_rubric_version_id=exam_versions[attempt.exam_id]
    )
