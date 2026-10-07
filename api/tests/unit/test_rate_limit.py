"""Counting how often one caller may try something.

Three properties, all deliberate: it refuses a caller who is over the limit;
an ordinary limit *allows* the call when Redis cannot answer, so a cache
outage does not lock the product; and a refusing limit (the credential
routes) refuses the call when Redis errors mid-check, since that is when a
spray would run. A switched-off Redis allows every call regardless.
"""

from __future__ import annotations

from contextlib import suppress

import pytest

from app.core import rate_limit
from app.core.rate_limit import Limit, TooManyRequests, caller_key, check, check_sign_in

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


async def test_an_unreachable_redis_allows_an_ordinary_call(monkeypatch: pytest.MonkeyPatch) -> None:
    # An ordinary (fail-open) limit lets the call through when Redis errors.
    monkeypatch.setattr(rate_limit, "get_redis", lambda: FakeRedis(broken=True))
    for _ in range(50):
        await check(LIMIT, "caller")


async def test_no_redis_at_all_allows_the_call(monkeypatch: pytest.MonkeyPatch) -> None:
    # `REDIS_DISABLED` is a supported deployment, and it must not mean "no
    # logins".
    monkeypatch.setattr(rate_limit, "get_redis", lambda: None)
    for _ in range(50):
        await check(LIMIT, "caller")


async def test_a_fail_closed_limit_refuses_when_redis_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """SEC-003: a credential route does not silently stop being limited the
    moment Redis breaks under load — that is when a spray would be running."""
    monkeypatch.setattr(rate_limit, "get_redis", lambda: FakeRedis(broken=True))
    strict = Limit(name="password-reset", allowance=2, window_seconds=60, on_redis_error="refuse")
    with pytest.raises(TooManyRequests) as raised:
        await check(strict, "caller")
    assert raised.value.details == {"retry_after": 60, "limit": "password-reset"}


async def test_a_fail_closed_limit_still_allows_when_redis_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """A switched-off Redis is a deployment choice, not a failure to guard
    against, so even a fail-closed limit lets the call through."""
    monkeypatch.setattr(rate_limit, "get_redis", lambda: None)
    strict = Limit(name="password-reset", allowance=2, window_seconds=60, on_redis_error="refuse")
    for _ in range(50):
        await check(strict, "caller")


def test_the_caller_is_the_client_address() -> None:
    assert caller_key(Request(host="203.0.113.7")) == "203.0.113.7"  # type: ignore[arg-type]


def test_a_proxied_caller_is_the_address_our_proxy_saw() -> None:
    """SEC-003: with one trusted hop the caller is the rightmost entry — the
    address our own load balancer appended — not the leftmost, which the
    caller writes and could set to anything."""
    request = Request(host="10.0.0.1", forwarded="203.0.113.9, 198.51.100.5")
    assert caller_key(request) == "198.51.100.5"  # type: ignore[arg-type]


def test_a_spoofed_leading_address_does_not_mint_a_fresh_bucket() -> None:
    """An attacker prepending a made-up address still counts under the one our
    proxy saw, so a spray cannot rotate its way around the limit."""
    real_peer = "198.51.100.5"
    a = Request(host="10.0.0.1", forwarded=f"1.1.1.1, {real_peer}")
    b = Request(host="10.0.0.1", forwarded=f"2.2.2.2, {real_peer}")
    assert caller_key(a) == real_peer  # type: ignore[arg-type]
    assert caller_key(b) == real_peer  # type: ignore[arg-type]


def test_a_caller_with_no_address_still_gets_a_bucket() -> None:
    assert caller_key(Request(host=None)) == "unknown"  # type: ignore[arg-type]


async def test_a_per_user_limit_counts_the_person_not_the_address(redis: FakeRedis) -> None:
    """E-23: two people behind one proxy each get their own allowance, and one
    person's allowance runs out wherever they call from."""
    import uuid

    from app.core.auth import Principal

    first, second = uuid.uuid4(), uuid.uuid4()
    count_call = rate_limit.per_user(LIMIT)
    for _ in range(LIMIT.allowance):
        await count_call(Principal(user_id=first, email="first@example.com"))
    await count_call(Principal(user_id=second, email="second@example.com"))

    with pytest.raises(TooManyRequests) as refused:
        await count_call(Principal(user_id=first, email="first@example.com"))
    assert refused.value.details == {"retry_after": 42, "limit": "test"}
    assert set(redis.counts) == {f"ratelimit:test:user:{first}", f"ratelimit:test:user:{second}"}


def test_the_per_user_limits_are_sized_for_what_each_call_costs() -> None:
    """The more a call costs somebody else, the fewer a person gets."""
    per_minute = {
        limit.name: limit.allowance / limit.window_seconds * 60
        for limit in (
            rate_limit.USER_WRITE,
            rate_limit.AI_SPEND,
            rate_limit.PUBLISH,
            rate_limit.OUTBOUND_EMAIL,
        )
    }
    assert per_minute["user-write"] > per_minute["ai-spend"] > per_minute["outbound-email"]
    assert per_minute["user-write"] > per_minute["publish"]


async def test_a_cohort_behind_one_address_can_all_sign_in(redis: FakeRedis) -> None:
    """S-6: forty trainees on one hospital NAT at exam start all get through,
    while ten wrong tries at one account still stop the eleventh."""
    ward = Request(host="198.51.100.9")
    for n in range(40):
        await check_sign_in(ward, f"trainee{n}@example.com")  # type: ignore[arg-type]

    for _ in range(9):
        await check_sign_in(ward, "Trainee0@Example.com ")  # type: ignore[arg-type]
    with pytest.raises(TooManyRequests) as raised:
        await check_sign_in(ward, "trainee0@example.com")  # type: ignore[arg-type]
    assert raised.value.details["limit"] == "sign-in", "the account ran out, not the address"
    assert not any("trainee0@example.com" in key for key in redis.counts), "no address in Redis keys"


async def test_sign_in_keeps_counting_in_process_when_redis_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """S-6 without undoing SEC-003: a Redis error mid-check neither refuses
    every sign-in nor stops limiting a guessed account."""
    monkeypatch.setattr(rate_limit, "get_redis", lambda: FakeRedis(broken=True))
    monkeypatch.setattr(rate_limit, "_local_windows", {})
    ward = Request(host="198.51.100.9")
    for _ in range(10):
        await check_sign_in(ward, "guessed@example.com")  # type: ignore[arg-type]
    with pytest.raises(TooManyRequests):
        await check_sign_in(ward, "guessed@example.com")  # type: ignore[arg-type]
    await check_sign_in(ward, "someone-else@example.com")  # type: ignore[arg-type]


async def test_one_address_spraying_many_accounts_is_stopped_at_its_ceiling(
    redis: FakeRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S-6 keeps the per-address brake: one machine trying a different account
    each time runs out of the address allowance, not any account's."""
    monkeypatch.setattr(
        rate_limit, "SIGN_IN_ADDRESS", Limit(name="sign-in-address", allowance=3, window_seconds=60)
    )
    sprayer = Request(host="203.0.113.66")
    for n in range(3):
        await check_sign_in(sprayer, f"victim{n}@example.com")  # type: ignore[arg-type]
    with pytest.raises(TooManyRequests) as raised:
        await check_sign_in(sprayer, "victim99@example.com")  # type: ignore[arg-type]
    assert raised.value.details["limit"] == "sign-in-address"


async def test_the_local_count_never_holds_more_than_its_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """A spray of fresh addresses during a Redis outage cannot grow memory without end."""
    monkeypatch.setattr(rate_limit, "get_redis", lambda: FakeRedis(broken=True))
    monkeypatch.setattr(rate_limit, "_local_windows", {})
    monkeypatch.setattr(rate_limit, "_LOCAL_MAX_KEYS", 5)
    counted = Limit(name="sign-in", allowance=10, window_seconds=60, on_redis_error="count_locally")
    for n in range(20):
        await check(counted, f"caller{n}")
    assert len(rate_limit._local_windows) == 5
