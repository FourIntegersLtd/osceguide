"""Our own workers' seats, and the waiting line for when every seat is taken.

`capacity` counts LiveKit Cloud. This counts the other half: the assessment
workers we run ourselves (3 nodes x 6 sessions in assessment-platform's k8s
config), and queues a candidate once both are full. Before it, candidate 19
was handed a token, joined an empty room and waited for a patient no worker
would accept.

Admission is one Lua script so it is atomic across API replicas: a candidate
takes a seat only if fewer people are ahead of them in line than there are
seats free. A newcomer is placed behind everyone already waiting, so a seat
that frees up is held for the person at the front until they come to claim it.

A waiter who stops watching (closed the tab, lost the connection) drops out
after `livekit_queue_waiter_ttl_seconds`. Their stream is what keeps them in
line: every snapshot refreshes their place.

Only this API writes these keys. Legacy b2c sessions that overflow onto the
same workers are not counted here, so until b2c-api retires the line can
admit a candidate the workers then refuse — which is no worse than before.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum

from app.core.logging import get_logger
from app.core.settings import Settings
from app.features.voice.capacity import CLOUD_SLOTS_KEY, run_script

log = get_logger(__name__)

# Rooms seated on our own assessment workers, scored by when the seat expires.
SEATS_KEY = "livekit:self_hosted_seats:assessment"
# Rooms waiting for a seat, scored by arrival, so rank is place in line.
QUEUE_KEY = "livekit:voice_queue:assessment"
# The same rooms, scored by when their watcher is presumed gone.
SEEN_KEY = "livekit:voice_queue_seen:assessment"

# Every script starts by forgetting expired seats and departed waiters, so a
# count is never inflated by a session that ended without saying so.
_PURGE = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', now)
for _, departed in ipairs(redis.call('ZRANGEBYSCORE', KEYS[4], '-inf', now)) do
  redis.call('ZREM', KEYS[3], departed)
  redis.call('ZREM', KEYS[4], departed)
end
"""

# Seat this room on Cloud or our own workers, or put it in line.
# KEYS: cloud, seats, queue, seen.
# ARGV: room, now, cloud_max, seats_max, pending_expiry, waiter_expiry, arrival.
# A room already seated keeps its seat (GT only ever lengthens it), because a
# candidate who reloads the page must not take a second one.
ADMIT = (
    """
local room = ARGV[1]
local now = tonumber(ARGV[2])
local cloud_max = tonumber(ARGV[3])
local seats_max = tonumber(ARGV[4])
local pending_expiry = tonumber(ARGV[5])
local waiter_expiry = tonumber(ARGV[6])
local arrival = tonumber(ARGV[7])
"""
    + _PURGE
    + """
if redis.call('ZSCORE', KEYS[1], room) then
  redis.call('ZADD', KEYS[1], 'GT', pending_expiry, room)
  return {'cloud', 0}
end
if redis.call('ZSCORE', KEYS[2], room) then
  redis.call('ZADD', KEYS[2], 'GT', pending_expiry, room)
  return {'self-hosted', 0}
end

local ahead = redis.call('ZRANK', KEYS[3], room)
if not ahead then
  ahead = redis.call('ZCARD', KEYS[3])
end
local cloud_free = math.max(0, cloud_max - redis.call('ZCARD', KEYS[1]))
local seats_free = math.max(0, seats_max - redis.call('ZCARD', KEYS[2]))

if ahead < cloud_free + seats_free then
  redis.call('ZREM', KEYS[3], room)
  redis.call('ZREM', KEYS[4], room)
  if cloud_free > 0 then
    redis.call('ZADD', KEYS[1], pending_expiry, room)
    return {'cloud', 0}
  end
  redis.call('ZADD', KEYS[2], pending_expiry, room)
  return {'self-hosted', 0}
end

redis.call('ZADD', KEYS[3], 'NX', arrival, room)
redis.call('ZADD', KEYS[4], waiter_expiry, room)
return {'queued', ahead + 1}
"""
)

# Where this room stands, for its waiting screen. Takes nothing, but refreshes
# the waiter's presence: being watched is what keeps a place in line.
# KEYS: cloud, seats, queue, seen. ARGV: room, now, cloud_max, seats_max, waiter_expiry.
STANDING = (
    """
local room = ARGV[1]
local now = tonumber(ARGV[2])
local cloud_max = tonumber(ARGV[3])
local seats_max = tonumber(ARGV[4])
local waiter_expiry = tonumber(ARGV[5])
"""
    + _PURGE
    + """
local ahead = redis.call('ZRANK', KEYS[3], room)
if not ahead then
  return {'ready', 0}
end
redis.call('ZADD', KEYS[4], waiter_expiry, room)
local cloud_free = math.max(0, cloud_max - redis.call('ZCARD', KEYS[1]))
local seats_free = math.max(0, seats_max - redis.call('ZCARD', KEYS[2]))
if ahead < cloud_free + seats_free then
  return {'ready', ahead + 1}
end
return {'waiting', ahead + 1}
"""
)

# Count a room against our own seats whatever the line says. For a circuit,
# which dispatches its own patient at a fixed time and must never wait.
HOLD = """
redis.call('ZADD', KEYS[1], 'GT', tonumber(ARGV[2]), ARGV[1])
return 1
"""

# Lengthen a held seat to a whole session once the worker arrives. A room that
# holds no seat here is on Cloud, and counting it would miscount both.
EXTEND = """
if redis.call('ZSCORE', KEYS[1], ARGV[1]) then
  redis.call('ZADD', KEYS[1], tonumber(ARGV[2]), ARGV[1])
  return 1
end
return 0
"""

RELEASE = """
return redis.call('ZREM', KEYS[1], ARGV[1])
"""

# Step out of line. Both keys in one script, so no reader sees a waiter whose
# presence is gone but whose place still counts. KEYS: queue, seen. ARGV: room.
LEAVE = """
local removed = redis.call('ZREM', KEYS[1], ARGV[1])
redis.call('ZREM', KEYS[2], ARGV[1])
return removed
"""

# How full our own seats and the line are, for the console. Purges like every
# other script, so the counts match what admission would see; takes nothing.
# KEYS: cloud, seats, queue, seen. ARGV: now.
COUNTS = (
    """
local now = tonumber(ARGV[1])
"""
    + _PURGE
    + """
return {redis.call('ZCARD', KEYS[2]), redis.call('ZCARD', KEYS[3])}
"""
)


class Placement(StrEnum):
    """Where a room was seated, or that it is waiting."""

    CLOUD = "cloud"
    SELF_HOSTED = "self-hosted"
    QUEUED = "queued"


@dataclass(frozen=True)
class Admission:
    """The outcome of asking for a seat. `position` is 1 for the front of the line, 0 when seated."""

    placement: Placement
    position: int


@dataclass(frozen=True)
class LineCounts:
    """Seats taken on our own workers and people waiting, as one consistent read."""

    seats_taken: int
    queue_length: int


@dataclass(frozen=True)
class Standing:
    """A waiter's place: `ready` means go and ask for the seat now."""

    ready: bool
    position: int


def _line_keys() -> tuple[str, str, str, str]:
    """The four keys admission reads, in the order every script expects them."""
    return (CLOUD_SLOTS_KEY, SEATS_KEY, QUEUE_KEY, SEEN_KEY)


async def admit(settings: Settings, room: str, *, use_cloud: bool) -> Admission:
    """Seat this room, preferring Cloud when `use_cloud`, or put it in line.

    Redis being unavailable seats it on our own workers, as the Cloud counter
    has always done: refusing every candidate over a cache outage is worse
    than risking a full worker.
    """
    now = time.time()
    pending_expiry = int(now) + max(60, settings.livekit_cloud_slot_pending_ttl_seconds)
    waiter_expiry = int(now) + settings.livekit_queue_waiter_ttl_seconds
    cloud_max = max(1, settings.livekit_cloud_max_concurrent) if use_cloud else 0
    try:
        raw = await run_script(
            ADMIT,
            _line_keys(),
            room,
            int(now),
            cloud_max,
            settings.livekit_self_hosted_seats,
            pending_expiry,
            waiter_expiry,
            int(now * 1000),
        )
    except Exception:  # noqa: BLE001 - Redis down means self-hosted, not refused
        log.warning("seat admission failed; serving self-hosted", room=room, exc_info=True)
        return Admission(Placement.SELF_HOSTED, 0)
    admission = Admission(Placement(str(raw[0])), int(raw[1]))
    log.info("seat admission", room=room, placement=admission.placement, position=admission.position)
    return admission


async def standing(settings: Settings, room: str, *, use_cloud: bool) -> Standing:
    """Where this room is in line. Not in line at all reads as ready: asking for a token decides."""
    now = int(time.time())
    cloud_max = max(1, settings.livekit_cloud_max_concurrent) if use_cloud else 0
    try:
        raw = await run_script(
            STANDING,
            _line_keys(),
            room,
            now,
            cloud_max,
            settings.livekit_self_hosted_seats,
            now + settings.livekit_queue_waiter_ttl_seconds,
        )
    except Exception:  # noqa: BLE001 - the token request falls back the same way
        log.warning("queue standing failed; reporting ready", room=room, exc_info=True)
        return Standing(ready=True, position=0)
    return Standing(ready=str(raw[0]) == "ready", position=int(raw[1]))


async def hold(settings: Settings, room: str) -> None:
    """Count a circuit's room against our seats. Best effort: a circuit never waits on it."""
    expiry = int(time.time()) + max(60, settings.livekit_cloud_slot_pending_ttl_seconds)
    try:
        await run_script(HOLD, (SEATS_KEY,), room, expiry)
    except Exception:  # noqa: BLE001 - a circuit never waits on the count
        log.warning("seat hold failed", room=room, exc_info=True)


async def extend(settings: Settings, room: str) -> bool:
    """Lengthen a room's seat to a whole session. False when it holds none here."""
    expiry = int(time.time()) + max(60, settings.livekit_cloud_slot_ttl_seconds)
    try:
        return bool(int(await run_script(EXTEND, (SEATS_KEY,), room, expiry)))
    except Exception:  # noqa: BLE001 - the pending seat still expires on its own
        log.warning("seat extend failed", room=room, exc_info=True)
        return False


async def release(room: str) -> bool:
    """Give a room's seat back. The expiry score reclaims it if this never arrives."""
    try:
        return bool(int(await run_script(RELEASE, (SEATS_KEY,), room)))
    except Exception:  # noqa: BLE001 - the expiry score reclaims it either way
        log.warning("seat release failed", room=room, exc_info=True)
        return False


async def leave(room: str) -> bool:
    """Take this room out of line. False when it was not in line, which is not an error."""
    return bool(int(await run_script(LEAVE, (QUEUE_KEY, SEEN_KEY), room)))


async def line_counts() -> LineCounts | None:
    """Seats taken and the line's length right now; None when Redis cannot say."""
    try:
        raw = await run_script(COUNTS, _line_keys(), int(time.time()))
    except Exception:  # noqa: BLE001 - a count nobody acts on automatically
        log.warning("seat count failed", exc_info=True)
        return None
    return LineCounts(seats_taken=int(raw[0]), queue_length=int(raw[1]))
