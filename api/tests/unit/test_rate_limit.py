"""Counting how often one caller may try something.

The two properties that matter are opposites, and both are deliberate: it
refuses a caller who is over the limit, and it *allows* every caller when
Redis cannot answer. Failing closed here would turn a cache outage into
nobody being able to sign in.
"""

from __future__ import annotations

from contextlib import suppress

import pytest

from app.core import rate_limit
from app.core.rate_limit import Limit, TooManyRequests, caller_key, check

LIMIT = Limit(name="test", allowance=2, window_seconds=60)


class FakeRedis:
    """Enough of Redis to count. Raises on demand, to prove the open failure."""

    def __init__(self, *, broken: bool = False) -> None:
        self.counts: dict[str, int] = {}
        self.expiries: list[tuple[str, int]] = []
        self.broken = broken

    async def incr(self, key: str) -> int:
        if self.broken:
            raise ConnectionError("redis is down")
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.expiries.append((key, seconds))

    async def ttl(self, key: str) -> int:
        return 42


class Request:
    def __init__(self, host: str | None = "203.0.113.1", forwarded: str | None = None) -> None:
        self.headers = {"x-forwarded-for": forwarded} if forwarded else {}
        self.client = type("C", (), {"host": host})() if host else None


@pytest.fixture
def redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    fake = FakeRedis()
    monkeypatch.setattr(rate_limit, "get_redis", lambda: fake)
    return fake


async def test_calls_inside_the_allowance_pass(redis: FakeRedis) -> None:
    await check(LIMIT, "caller")
    await check(LIMIT, "caller")


async def test_the_call_past_the_allowance_is_refused(redis: FakeRedis) -> None:
    await check(LIMIT, "caller")
    await check(LIMIT, "caller")
    with pytest.raises(TooManyRequests) as raised:
        await check(LIMIT, "caller")
    assert raised.value.status == 429
    # The client is told how long to wait, so it can back off rather than
    # retry into the same wall.
    assert raised.value.details == {"retry_after": 42, "limit": "test"}


async def test_one_caller_does_not_spend_anothers_allowance(redis: FakeRedis) -> None:
    for _ in range(3):
        with suppress(TooManyRequests):
            await check(LIMIT, "noisy")
    await check(LIMIT, "quiet")


async def test_the_window_is_set_once_per_window(redis: FakeRedis) -> None:
    """Otherwise a burst keeps pushing the window out in front of itself and
    the limit never resets."""
    await check(LIMIT, "caller")
    await check(LIMIT, "caller")
    assert len(redis.expiries) == 1


async def test_an_unreachable_redis_allows_the_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rate_limit, "get_redis", lambda: FakeRedis(broken=True))
    for _ in range(50):
        await check(LIMIT, "caller")


async def test_no_redis_at_all_allows_the_call(monkeypatch: pytest.MonkeyPatch) -> None:
    # `REDIS_DISABLED` is a supported deployment, and it must not mean "no
    # logins".
    monkeypatch.setattr(rate_limit, "get_redis", lambda: None)
    for _ in range(50):
        await check(LIMIT, "caller")


def test_the_caller_is_the_client_address() -> None:
    assert caller_key(Request(host="203.0.113.7")) == "203.0.113.7"  # type: ignore[arg-type]


def test_a_proxied_caller_is_the_first_forwarded_address() -> None:
    """Behind a load balancer every caller shares its address, so without
    this one bucket is shared by everybody and the limit is useless."""
    request = Request(host="10.0.0.1", forwarded="203.0.113.9, 10.0.0.1")
    assert caller_key(request) == "203.0.113.9"  # type: ignore[arg-type]


def test_a_caller_with_no_address_still_gets_a_bucket() -> None:
    assert caller_key(Request(host=None)) == "unknown"  # type: ignore[arg-type]
