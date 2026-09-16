from __future__ import annotations

import asyncio

from redis.asyncio import Redis

from app import __version__
from app.core.db import Connection
from app.core.logging import get_logger
from app.features.health import repository
from app.features.health.schemas import CheckState, HealthResponse

log = get_logger(__name__)
CHECK_TIMEOUT_SECONDS = 2.0


async def check_database(conn: Connection) -> CheckState:
    try:
        await asyncio.wait_for(repository.ping(conn), CHECK_TIMEOUT_SECONDS)
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


async def health_report(conn: Connection, redis: Redis | None) -> HealthResponse:
    checks = {"database": await check_database(conn), "redis": await check_redis(redis)}
    if checks["database"] == "error":
        status = "down"
    elif checks["redis"] == "error":
        status = "degraded"
    else:
        status = "ok"
    return HealthResponse(status=status, version=__version__, checks=checks)
