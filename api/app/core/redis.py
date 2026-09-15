"""Redis client for ephemeral state only: cache, rate limits, SSE fan-out, LiveKit
cloud-slot counters. Nothing durable lives here; durable work goes through
Postgres and the job queue.

Short timeouts keep a Redis outage from stalling requests; callers must treat
`None` as "Redis is off" and degrade.
"""

from __future__ import annotations

from redis.asyncio import Redis, from_url

from app.core.settings import get_settings

_client: Redis | None = None


def get_redis() -> Redis | None:
    global _client
    settings = get_settings()
    if settings.redis_disabled or not settings.redis_url:
        return None
    if _client is None:
        _client = from_url(
            settings.redis_url,
            socket_connect_timeout=1.5,
            socket_timeout=2.0,
            decode_responses=True,
        )
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
    _client = None
