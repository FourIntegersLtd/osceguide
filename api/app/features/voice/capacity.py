"""How many LiveKit Cloud sessions are running, across every product.

Cloud concurrency is metered and billed. b2c, b2b and this slice all count it in
the same Redis sorted set under the same key, so the scripts and key name are
**byte-identical** to `b2c/shared/services/livekit_cloud_capacity.py` — otherwise
they would disagree about how full Cloud is. Scored by expiry, not a plain
counter, so a worker that dies without releasing its slot does not hold it
forever. Redis being unavailable means "no free slots", not "unlimited".
"""

from __future__ import annotations

import time
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any, cast

from app.core.logging import get_logger
from app.core.redis import get_redis
from app.core.settings import Settings

log = get_logger(__name__)

# Shared with b2c and b2b. Do not rename while any of them is still running.
CLOUD_SLOTS_KEY = "livekit:cloud_active_slots"

# Reserve, or confirm an existing reservation, dropping expired rooms first.
# Re-reserving a room already held refreshes it instead of double-counting,
# because a candidate who reloads the page must not consume a second slot.
RESERVE = """
local key = KEYS[1]
local room = ARGV[1]
local max_slots = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local expiry = tonumber(ARGV[4])

redis.call('ZREMRANGEBYSCORE', key, '-inf', now)

if redis.call('ZSCORE', key, room) then
  redis.call('ZADD', key, expiry, room)
  return {1, redis.call('ZCARD', key)}
end

local count = redis.call('ZCARD', key)
if count >= max_slots then
  return {0, count}
end

redis.call('ZADD', key, expiry, room)
return {1, count + 1}
"""

# Count what is held, dropping expired rooms first, without holding anything.
# For the console: `try_reserve` answers "may this room run" by taking a slot,
# which is the wrong question for somebody only looking.
ACTIVE = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', tonumber(ARGV[1]))
return redis.call('ZCARD', KEYS[1])
"""

RELEASE = """
local removed = redis.call('ZREM', KEYS[1], ARGV[1])
return {removed, redis.call('ZCARD', KEYS[1])}
"""

EXTEND = """
local key = KEYS[1]
local room = ARGV[1]
local expiry = tonumber(ARGV[2])
if redis.call('ZSCORE', key, room) then
  redis.call('ZADD', key, expiry, room)
  return 1
end
return 0
"""


async def _run(script: str, *args: object) -> Any:
    """Run one of the scripts, or raise. Arguments go as strings, as redis-py puts
    on the wire anyway; Lua's `tonumber` reads them back.
    """
    client = get_redis()
    if client is None:
        raise ConnectionError("redis is not configured")
    return await cast(
        "Awaitable[Any]", client.eval(script, 1, CLOUD_SLOTS_KEY, *[str(argument) for argument in args])
    )


@dataclass(frozen=True)
class Reservation:
    """Whether a Cloud slot was held, and how many are active if the caller asked."""

    reserved: bool
    active_count: int | None


async def try_reserve(settings: Settings, room: str) -> Reservation:
    """Hold a Cloud slot for this room until the worker connects or it expires.

    The short pending TTL is what stops an abandoned ticket holding a slot for
    the length of a session; `extend` lengthens it once a worker actually
    arrives.
    """
    client = get_redis()
    if client is None or not room:
        return Reservation(reserved=False, active_count=None)

    now = int(time.time())
    expiry = now + max(60, settings.livekit_cloud_slot_pending_ttl_seconds)
    try:
        raw = await _run(RESERVE, room, max(1, settings.livekit_cloud_max_concurrent), now, expiry)
    except Exception:  # noqa: BLE001 - Redis down means self-hosted, not refused
        log.warning("cloud slot reserve failed; serving self-hosted", room=room, exc_info=True)
        return Reservation(reserved=False, active_count=None)

    reserved, active = bool(int(raw[0])), int(raw[1])
    log.info(
        "cloud slot reserve",
        room=room,
        reserved=reserved,
        active_count=active,
        max_concurrent=settings.livekit_cloud_max_concurrent,
    )
    return Reservation(reserved=reserved, active_count=active)


async def release(settings: Settings, room: str) -> bool:
    """Give the slot back. Best effort: the worker never reads the answer."""
    client = get_redis()
    if client is None or not room:
        return False
    try:
        raw = await _run(RELEASE, room)
    except Exception:  # noqa: BLE001 - the expiry score reclaims it either way
        log.warning("cloud slot release failed", room=room, exc_info=True)
        return False
    removed, active = bool(int(raw[0])), int(raw[1])
    log.info("cloud slot release", room=room, removed=removed, active_count=active)
    return removed


async def extend(settings: Settings, room: str) -> bool:
    """Lengthen a held slot to a full session once a worker has connected.

    Only extends a room that already holds one: a worker in a room nobody
    reserved is self-hosted, and granting it a Cloud slot would miscount.
    """
    client = get_redis()
    if client is None or not room:
        return False
    expiry = int(time.time()) + max(60, settings.livekit_cloud_slot_ttl_seconds)
    try:
        raw = await _run(EXTEND, room, expiry)
    except Exception:  # noqa: BLE001
        log.warning("cloud slot extend failed", room=room, exc_info=True)
        return False
    extended = bool(int(raw))
    log.info("cloud slot extend", room=room, extended=extended)
    return extended


async def slots_free(settings: Settings, room: str) -> bool:
    """Whether this room may run on Cloud.

    Overflow **disabled** means Cloud is used as configured and nothing is
    metered, not that Cloud is off. When enabled, reserving *is* the question:
    asking how many slots are free and then taking one would race.
    """
    if not settings.livekit_cloud_overflow_enabled:
        return True
    return (await try_reserve(settings, room)).reserved


async def active_slots() -> int | None:
    """How many Cloud sessions are held right now; None when Redis cannot say."""
    if get_redis() is None:
        return None
    try:
        return int(await _run(ACTIVE, int(time.time())))
    except Exception:  # noqa: BLE001 - a count nobody acts on automatically
        log.warning("cloud slot count failed", exc_info=True)
        return None
