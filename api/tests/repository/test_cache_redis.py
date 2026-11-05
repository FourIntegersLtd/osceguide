"""`core.cache` against a real Redis (the `seat_redis` fixture)."""

from __future__ import annotations

import asyncio
import json
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import cache


@pytest.fixture(autouse=True)
def _point_cache_at_test_redis(seat_redis: object, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cache, "get_redis", lambda: seat_redis)


async def test_miss_stores_with_a_ttl_and_ten_concurrent_misses_load_once(seat_redis: object) -> None:
    key = f"test:{uuid.uuid4().hex}"
    calls = 0

    async def load() -> list[int]:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return [1, 2, 3]

    got = await asyncio.gather(
        *[cache.get_or_load(key, 30, load, dump=json.dumps, parse=json.loads) for _ in range(10)]
    )
    assert got == [[1, 2, 3]] * 10
    assert calls == 1
    ttl = await seat_redis.ttl(f"cache:{key}")  # type: ignore[attr-defined]
    assert 0 < ttl <= 30
    await seat_redis.delete(f"cache:{key}")  # type: ignore[attr-defined]


async def test_bump_and_forget_apply_after_commit(seat_redis: object, db_session: AsyncSession) -> None:
    name = f"test{uuid.uuid4().hex}"
    await seat_redis.set(f"cache:{name}", "x")  # type: ignore[attr-defined]
    cache.bump_after_commit(db_session, name)
    cache.forget_after_commit(db_session, name)
    assert await cache.version(name) == 0
    await cache.flush_cache_ops(db_session)
    assert await cache.version(name) == 1
    assert await seat_redis.get(f"cache:{name}") is None  # type: ignore[attr-defined]
    await seat_redis.delete(f"cache:ver:{name}")  # type: ignore[attr-defined]
