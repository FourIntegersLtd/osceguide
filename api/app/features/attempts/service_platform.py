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
from collections.abc import Collection
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import domain, errors, repository, repository_platform
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.jobs import SCORING_TASK
from app.features.attempts.models import Attempt
from app.features.attempts.repository_platform import VersionProgress
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
    attempts, next_cursor = await repository.list_for_user(
        session,
        user_id,
        limit=limit,
        cursor=cursor,
        status=domain.Status(status) if status else None,
    )
    ids = [attempt.id for attempt in attempts]
    delivered = await transcripts.transcripts_for(session, ids)
    versions = await transcripts.policy_versions_for(session, ids)
    jobs = await _jobs_by_attempt(session, ids)
    return [
        _read(
            attempt,
            transcript=delivered.get(attempt.id),
            versions=versions.get(attempt.id, []),
            latest_job=_latest(jobs.get(attempt.id, [])),
        )
        for attempt in attempts
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
        session,
        task_name=SCORING_TASK,
        key="attempt_id",
        values=[str(attempt_id) for attempt_id in attempt_ids],
    )
    jobs_by_attempt: dict[uuid.UUID, list[ScoringJobRead]] = {}
    for job in found:
        jobs_by_attempt.setdefault(uuid.UUID(str(job.args.get("attempt_id"))), []).append(
            ScoringJobRead(
                id=job.id,
                status=job.status,
                attempts=job.attempts,
                policy_version=job.args.get("policy_version"),
                scheduled_at=job.scheduled_at,
            )
        )
    return jobs_by_attempt


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


# --- A person's attempts as the console sees them, by station.


async def attempted_user_ids(session: AsyncSession) -> set[uuid.UUID]:
    """Everyone who has started at least one attempt."""
    return await repository_platform.attempted_user_ids(session)


async def attempt_counts(session: AsyncSession, user_ids: Collection[uuid.UUID]) -> dict[uuid.UUID, int]:
    return await repository_platform.count_by_user(session, user_ids)


async def progress_by_version(session: AsyncSession, user_id: uuid.UUID) -> list[VersionProgress]:
    """One row per station version this person has sat, newest first."""
    if await identity.user_ref_by_id(session, user_id) is None:
        raise errors.UserNotFound()
    return await repository_platform.progress_by_version(session, user_id)


async def delete_progress(
    session: AsyncSession, user_id: uuid.UUID, version_ids: Collection[uuid.UUID]
) -> int:
    """Erase this person's attempts at these versions. Refused while one is
    still running: a consultation in progress would lose its room from under
    it, and the worker would write turns against a row that no longer exists.
    """
    if await identity.user_ref_by_id(session, user_id) is None:
        raise errors.UserNotFound()
    if await repository_platform.running_for_user_versions(session, user_id, version_ids):
        raise errors.AttemptInProgress()
    return await repository_platform.delete_for_user_versions(session, user_id, version_ids)
