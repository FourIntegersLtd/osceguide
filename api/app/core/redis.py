"""Redis client for ephemeral state only: cache, rate limits, SSE fan-out, LiveKit
cloud-slot counters. Nothing durable lives here; durable work goes through
Postgres and the job queue.

Short timeouts keep a Redis outage from stalling requests; callers must treat
`None` as "Redis is off" and degrade.
"""

from __future__ import annotations

import socket

from redis.asyncio import Redis

from app.core.settings import get_settings

_client: Redis | None = None

# Probe a silent link after 20 s, every 10 s, give up after 3 misses: dead in about 50 s.
# `TCP_KEEPIDLE` is Linux; macOS spells the first one `TCP_KEEPALIVE`.
_KEEPALIVE_OPTIONS: dict[int, int] = {
    getattr(socket, "TCP_KEEPIDLE", getattr(socket, "TCP_KEEPALIVE", 0x10)): 20,
    socket.TCP_KEEPINTVL: 10,
    socket.TCP_KEEPCNT: 3,
}


def get_redis() -> Redis | None:
    """The shared client, or `None` when Redis is disabled or unconfigured."""
    global _client
    settings = get_settings()
    if settings.redis_disabled or not settings.redis_url:
        return None
    if _client is None:
        _client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1.5,
            socket_timeout=2.0,
            decode_responses=True,
        )
    return _client


def new_subscriber_client() -> Redis:
    """A client of its own for the event bus's one pub/sub connection.

    Not the shared client: that one has a two-second read timeout, and a
    subscription spends its life waiting for a message. TCP keepalive is how a
    half-open link (a failover or NAT drop that sends no reset) is noticed
    without one: the blocked read then fails after about a minute.
    """
    settings = get_settings()
    client: Redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=1.5,
        socket_timeout=None,
        socket_keepalive=True,
        socket_keepalive_options=_KEEPALIVE_OPTIONS,
    )
    return client


async def close_redis() -> None:
    """Close the shared client, if one was ever opened. Called at shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
    _client = None
