"""Short-lived shared cache in Redis. Redis off or failing => every call loads fresh.

Not a store of record: a value here is a copy of something Postgres holds, kept for seconds or
minutes so a spike of identical reads (a library page, an auth status) hits the database once.
Every Redis failure is logged at debug level and ignored, so an outage costs speed, never answers.

- `get_or_load` reads through the cache, with one load per key per process while a miss is in flight.
- `version` / `bump_after_commit` give a family of keys a counter: build keys with `version(name)`
  in them and a bump makes every older key unreachable (it expires on its own).
- `forget_after_commit` deletes one key. Both queue on the session and run only once the
  transaction has committed (`flush_cache_ops`, called by `core.db`), the way `publish_after_commit`
  holds events: a rolled-back request must not invalidate, and an early invalidation would let a
  reader re-fill the cache with the old row.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Literal, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

T = TypeVar("T")

KEY_PREFIX = "cache"
PENDING_KEY = "cache_ops"

CacheOp = tuple[Literal["bump", "forget"], str]

# Raw cached text of loads in flight in this process; None if that load failed.
_inflight: dict[str, asyncio.Future[str | None]] = {}


def _full_key(key: str) -> str:
    return f"{KEY_PREFIX}:{key}"


def _version_key(name: str) -> str:
    return f"{KEY_PREFIX}:ver:{name}"


async def get_or_load(
    key: str,
    ttl_seconds: int,
    load: Callable[[], Awaitable[T]],
    *,
    dump: Callable[[T], str],
    parse: Callable[[str], T],
) -> T:
    """The cached value for `key`, loading and storing it on a miss.

    Concurrent misses for one key in this process share a single `load`. A load that raises is not
    cached, and each waiting caller then runs its own.
    """
    client = get_redis()
    if client is None:
        return await load()
    try:
        raw = await client.get(_full_key(key))
    except Exception as exc:  # noqa: BLE001 - any Redis failure means load fresh
        logger.debug("cache get failed for %s: %s", key, exc)
        return await load()
    if raw is not None:
        return parse(raw)

    pending = _inflight.get(key)
    if pending is not None:
        shared = await pending
        return parse(shared) if shared is not None else await load()

    # No await between the check above and this registration, so exactly one caller leads.
    future: asyncio.Future[str | None] = asyncio.get_running_loop().create_future()
    _inflight[key] = future
    try:
        value = await load()
        dumped = dump(value)
        try:
            await client.set(_full_key(key), dumped, ex=ttl_seconds)
        except Exception as exc:  # noqa: BLE001
            logger.debug("cache set failed for %s: %s", key, exc)
        future.set_result(dumped)
        return value
    except BaseException:
        if not future.done():
            future.set_result(None)
        raise
    finally:
        _inflight.pop(key, None)


async def version(name: str) -> int:
    """The counter for a family of keys; 0 when unset or when Redis is off or failing."""
    client = get_redis()
    if client is None:
        return 0
    try:
        raw = await client.get(_version_key(name))
        return int(raw) if raw is not None else 0
    except Exception as exc:  # noqa: BLE001
        logger.debug("cache version read failed for %s: %s", name, exc)
        return 0


def bump_after_commit(session: AsyncSession, name: str) -> None:
    """Raise `name`'s version once this transaction commits, orphaning every key built from the old one."""
    session.info.setdefault(PENDING_KEY, []).append(("bump", name))


def forget_after_commit(session: AsyncSession, key: str) -> None:
    """Delete `key` once this transaction commits."""
    session.info.setdefault(PENDING_KEY, []).append(("forget", key))


class ActiveOnlyRefusal(Exception):  # noqa: N818 - control flow out of `get_or_load`, never an error
    """A loader refused to store its answer in an active-only cache slot."""

    def __init__(self, detail: object) -> None:
        self.detail = detail


async def confirm_active_cached(
    key: str,
    ttl: int,
    *,
    fresh: bool,
    confirm_active: Callable[[], Awaitable[None]],
) -> ActiveOnlyRefusal | None:
    """Cache only when `confirm_active` completes. Returns a refusal to map to an error, else None."""
    if fresh or ttl <= 0:
        try:
            await confirm_active()
            return None
        except ActiveOnlyRefusal as refusal:
            return refusal

    async def load() -> str:
        """Looks the account up afresh once the remembered answer has expired."""
        await confirm_active()
        return "active"

    try:
        await get_or_load(key, ttl, load, dump=str, parse=str)
        return None
    except ActiveOnlyRefusal as refusal:
        return refusal


async def flush_cache_ops(session: AsyncSession) -> None:
    """Run what the committed transaction queued. Called by `core.db` only; a rollback never calls it."""
    ops: list[CacheOp] = session.info.pop(PENDING_KEY, [])
    if not ops:
        return
    client = get_redis()
    if client is None:
        return
    for action, name in ops:
        try:
            if action == "bump":
                await client.incr(_version_key(name))
            else:
                await client.delete(_full_key(name))
        except Exception as exc:  # noqa: BLE001
            logger.debug("cache %s failed for %s: %s", action, name, exc)
