"""What the console asks about the platform's own machinery.

`/health` says whether the database and Redis answer; a deploy checks it. The
console needs the next question — is anybody working the queue, and what is
stuck in it — which is answered from procrastinate's own tables.
"""

from __future__ import annotations

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.health import repository_jobs, service
from app.features.health.repository_jobs import JobRef
from app.features.health.schemas import JobRead, JobsPage, PlatformHealth


async def platform_health(session: AsyncSession, redis: Redis | None) -> PlatformHealth:
    report = await service.health_report(session, redis)
    return PlatformHealth(
        **report.model_dump(),
        jobs_by_status=await repository_jobs.counts_by_status(session),
        worker_seen_at=await repository_jobs.latest_worker_heartbeat(session),
    )


async def list_jobs(
    session: AsyncSession,
    *,
    status: str | None,
    task_name: str | None,
    before_id: int | None,
    limit: int,
) -> JobsPage:
    rows = await repository_jobs.list_jobs(
        session, status=status, task_name=task_name, before_id=before_id, limit=limit + 1
    )
    page = rows[:limit]
    return JobsPage(
        items=[_read(row) for row in page],
        next_before_id=page[-1].id if len(rows) > limit else None,
    )


def _read(row: JobRef) -> JobRead:
    return JobRead(
        id=row.id,
        queue_name=row.queue_name,
        task_name=row.task_name,
        status=row.status,
        attempts=row.attempts,
        scheduled_at=row.scheduled_at,
        args=row.args,
        queueing_lock=row.queueing_lock,
    )
