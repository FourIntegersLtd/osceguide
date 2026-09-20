"""Attempts as the people who answer support see them.

"I did the station and got no feedback" has four different causes, and the
candidate-facing reads say nothing that tells them apart: the worker never
delivered a transcript; it did and the attempt never left `running`; the
marking was never queued; or it was queued and failed. Each is a different
row — the attempt, its transcript record, the queue — and this puts them side
by side for one person's attempts.

Reads only. The actions that fix what these reveal live in
`service_platform_actions`.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import domain, errors, repository
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.jobs import SCORING_TASK
from app.features.attempts.models import Attempt
from app.features.attempts.schemas_platform import (
    PlatformAttemptDetail,
    PlatformAttemptRead,
    ScoringJobRead,
)
from app.features.health import service_jobs
from app.features.identity import service as identity


async def list_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None,
    status: str | None = None,
) -> tuple[list[PlatformAttemptRead], str | None]:
    """One person's attempts, newest first, each with its marking state."""
    if await identity.user_ref_by_id(session, user_id) is None:
        raise errors.UserNotFound()
    rows, next_cursor = await repository.list_for_user(
        session,
        user_id,
        limit=limit,
        cursor=cursor,
        status=domain.Status(status) if status else None,
    )
    ids = [row.id for row in rows]
    delivered = await transcripts.transcripts_for(session, ids)
    versions = await transcripts.policy_versions_for(session, ids)
    jobs = await _jobs_by_attempt(session, ids)
    return [
        _read(
            row,
            transcript=delivered.get(row.id),
            versions=versions.get(row.id, []),
            latest_job=_latest(jobs.get(row.id, [])),
        )
        for row in rows
    ], next_cursor


async def read_detail(session: AsyncSession, attempt_id: uuid.UUID) -> PlatformAttemptDetail:
    attempt = await repository.attempt_by_id(session, attempt_id)
    if attempt is None:
        raise errors.AttemptNotFound()
    jobs = (await _jobs_by_attempt(session, [attempt.id])).get(attempt.id, [])
    base = _read(
        attempt,
        transcript=await transcripts.transcript_for(session, attempt.id),
        versions=list(await transcripts.scored_policy_versions(session, attempt.id)),
        latest_job=_latest(jobs),
    )
    return PlatformAttemptDetail(
        **base.model_dump(),
        has_definition=bool(attempt.definition),
        definition_frozen_at=attempt.definition_frozen_at,
        chunk_count=await transcripts.chunk_count(session, attempt.id),
        jobs=jobs,
    )


async def _jobs_by_attempt(
    session: AsyncSession, attempt_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[ScoringJobRead]]:
    found = await service_jobs.jobs_for_arg(
        session, task_name=SCORING_TASK, key="attempt_id", values=[str(i) for i in attempt_ids]
    )
    out: dict[uuid.UUID, list[ScoringJobRead]] = {}
    for job in found:
        out.setdefault(uuid.UUID(str(job.args.get("attempt_id"))), []).append(
            ScoringJobRead(
                id=job.id,
                status=job.status,
                attempts=job.attempts,
                policy_version=job.args.get("policy_version"),
                scheduled_at=job.scheduled_at,
            )
        )
    return out


def _latest(jobs: list[ScoringJobRead]) -> ScoringJobRead | None:
    return max(jobs, key=lambda job: job.id, default=None)


def _read(
    attempt: Attempt,
    *,
    transcript: Any | None,
    versions: list[str],
    latest_job: ScoringJobRead | None,
) -> PlatformAttemptRead:
    return PlatformAttemptRead(
        id=attempt.id,
        kind=attempt.kind,
        status=attempt.status,
        exam_id=attempt.exam_id,
        station_version_id=attempt.station_version_id,
        room_name=attempt.room_name,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        created_at=attempt.created_at,
        user_id=attempt.user_id,
        org_id=attempt.org_id,
        failed_reason=attempt.failed_reason,
        transcript_complete=bool(transcript and transcript.complete),
        transcript_delivered_at=transcript.delivered_at if transcript else None,
        result_policy_versions=sorted(versions),
        scoring_job=latest_job,
    )
