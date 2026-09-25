from __future__ import annotations

import asyncio

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.logging import get_logger
from app.features.health import repository, repository_jobs
from app.features.health.repository_jobs import JobRef
from app.features.health.schemas import CheckState, HealthResponse, JobRead, JobsPage, PlatformHealth

log = get_logger(__name__)
CHECK_TIMEOUT_SECONDS = 2.0


async def check_database(session: AsyncSession) -> CheckState:
    try:
        await asyncio.wait_for(repository.ping(session), CHECK_TIMEOUT_SECONDS)
        return "ok"
    except Exception as exc:  # noqa: BLE001 - health must never raise
        log.warning("database check failed", error=str(exc))
        return "error"


async def check_redis(redis: Redis | None) -> CheckState:
    if redis is None:
        return "disabled"
    try:
        await asyncio.wait_for(redis.ping(), CHECK_TIMEOUT_SECONDS)
        return "ok"
    except Exception as exc:  # noqa: BLE001
        log.warning("redis check failed", error=str(exc))
        return "error"


async def health_report(session: AsyncSession, redis: Redis | None) -> HealthResponse:
    checks = {"database": await check_database(session), "redis": await check_redis(redis)}
    if checks["database"] == "error":
        status = "down"
    elif checks["redis"] == "error":
        status = "degraded"
    else:
        status = "ok"
    return HealthResponse(status=status, version=__version__, checks=checks)


# --- What the console asks about the platform's own machinery.


async def platform_health(session: AsyncSession, redis: Redis | None) -> PlatformHealth:
    report = await health_report(session, redis)
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
