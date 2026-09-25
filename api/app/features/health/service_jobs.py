"""The queue, as other features may ask about it.

`JobRef` is re-exported so a caller names one type; the SQL stays in `repository_jobs`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.health import repository_jobs
from app.features.health.repository_jobs import JOB_STATUSES, JobRef

__all__ = [
    "JOB_STATUSES",
    "JobRef",
    "counts_by_status",
    "jobs_for_arg",
    "latest_worker_heartbeat",
    "list_jobs",
]


async def jobs_for_arg(
    session: AsyncSession, *, task_name: str, key: str, values: Sequence[str]
) -> list[JobRef]:
    return await repository_jobs.jobs_for_arg(session, task_name=task_name, key=key, values=values)


async def list_jobs(
    session: AsyncSession,
    *,
    status: str | None = None,
    task_name: str | None = None,
    before_id: int | None = None,
    limit: int = 50,
) -> list[JobRef]:
    return await repository_jobs.list_jobs(
        session, status=status, task_name=task_name, before_id=before_id, limit=limit
    )


async def counts_by_status(session: AsyncSession) -> dict[str, int]:
    return await repository_jobs.counts_by_status(session)


async def latest_worker_heartbeat(session: AsyncSession) -> datetime | None:
    return await repository_jobs.latest_worker_heartbeat(session)
