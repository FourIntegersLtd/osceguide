"""`core.cache` with an in-memory stand-in for Redis: the contract that holds without a server."""

from __future__ import annotations

import asyncio
import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import cache


class FakeRedis:
    def __init__(self, *, broken: bool = False) -> None:
        self.data: dict[str, str] = {}
        self.broken = broken

    def _check(self) -> None:
        if self.broken:
            raise ConnectionError("down")

    async def get(self, key: str) -> str | None:
        self._check()
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._check()
        self.data[key] = value

    async def incr(self, key: str) -> int:
        self._check()
        self.data[key] = str(int(self.data.get(key, "0")) + 1)
        return int(self.data[key])

    async def delete(self, key: str) -> None:
        self._check()
        self.data.pop(key, None)


class Loader:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self) -> dict[str, int]:
        self.calls += 1
        await asyncio.sleep(0.01)
        return {"n": self.calls}


def _use(monkeypatch: pytest.MonkeyPatch, client: FakeRedis | None) -> None:
    monkeypatch.setattr(cache, "get_redis", lambda: client)


async def _get(loader: Loader, key: str = "k") -> dict[str, int]:
    return await cache.get_or_load(key, 60, loader, dump=json.dumps, parse=json.loads)


async def test_redis_off_loads_every_time(monkeypatch: pytest.MonkeyPatch) -> None:
    _use(monkeypatch, None)
    loader = Loader()
    assert await _get(loader) == {"n": 1}
    assert await _get(loader) == {"n": 2}
    assert await cache.version("x") == 0


async def test_a_hit_skips_the_load(monkeypatch: pytest.MonkeyPatch) -> None:
    _use(monkeypatch, FakeRedis())
    loader = Loader()
    assert await _get(loader) == {"n": 1}
    assert await _get(loader) == {"n": 1}
    assert loader.calls == 1


async def test_ten_concurrent_misses_load_once(monkeypatch: pytest.MonkeyPatch) -> None:
    _use(monkeypatch, FakeRedis())
    loader = Loader()
    results = await asyncio.gather(*[_get(loader) for _ in range(10)])
    assert loader.calls == 1
    assert results == [{"n": 1}] * 10


async def test_a_failed_load_is_not_cached_and_waiters_load_for_themselves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use(monkeypatch, FakeRedis())
    calls = 0

    async def flaky() -> dict[str, int]:
        nonlocal calls
        calls += 1
        n = calls
        await asyncio.sleep(0.01)
        if n == 1:
            raise RuntimeError("boom")
        return {"n": n}

    results = await asyncio.gather(
        cache.get_or_load("k", 60, flaky, dump=json.dumps, parse=json.loads),
        cache.get_or_load("k", 60, flaky, dump=json.dumps, parse=json.loads),
        return_exceptions=True,
    )
    assert isinstance(results[0], RuntimeError)
    assert results[1] == {"n": 2}
    assert cache._inflight == {}


async def test_a_broken_redis_loads_fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    _use(monkeypatch, FakeRedis(broken=True))
    loader = Loader()
    assert await _get(loader) == {"n": 1}
    assert await _get(loader) == {"n": 2}
    assert await cache.version("x") == 0


async def test_a_bump_changes_the_key_a_caller_builds(
    monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
) -> None:
    _use(monkeypatch, FakeRedis())
    before = f"library:{await cache.version('library')}"
    cache.bump_after_commit(db_session, "library")
    assert await cache.version("library") == 0  # queued, not yet committed
    await cache.flush_cache_ops(db_session)
    assert f"library:{await cache.version('library')}" != before
    assert await cache.version("library") == 1


async def test_forget_runs_after_commit_and_never_on_rollback(
    monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
) -> None:
    client = FakeRedis()
    _use(monkeypatch, client)
    client.data["cache:k"] = "1"
    cache.forget_after_commit(db_session, "k")
    assert "cache:k" in client.data
    # A rollback never reaches flush_cache_ops; the queued op is simply discarded with the session.
    db_session.info.pop(cache.PENDING_KEY)
    await cache.flush_cache_ops(db_session)
    assert "cache:k" in client.data
    cache.forget_after_commit(db_session, "k")
    await cache.flush_cache_ops(db_session)
    assert "cache:k" not in client.data
