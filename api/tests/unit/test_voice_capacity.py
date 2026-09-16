"""Cloud slot accounting, against a Redis that behaves like the real one.

b2c and b2b both count Cloud concurrency in the same sorted set under the same
key, and this is a third writer of it during coexistence. The scripts are
copied byte-identical from `b2c/shared/services/livekit_cloud_capacity.py` for
that reason, so these tests are really about the semantics the three share: a
re-reservation must not double count, an expired room must not hold a slot,
and Redis being unavailable must mean "serve it ourselves" rather than
"unlimited".
"""

from __future__ import annotations

import time

import pytest

from app.core.settings import Settings
from app.features.voice import capacity


class FakeRedis:
    """A sorted set and an `eval` that runs the three scripts' semantics.

    Not a mock: the scripts are the thing under test, so the fake implements
    what Redis would do with them rather than recording that they were called.
    """

    def __init__(self) -> None:
        self.zset: dict[str, float] = {}
        self.fail = False

    async def eval(self, script: str, _numkeys: int, _key: str, *args: object) -> object:
        if self.fail:
            raise ConnectionError("redis is down")
        if script is capacity.RESERVE:
            room, max_slots, now, expiry = str(args[0]), int(args[1]), int(args[2]), int(args[3])
            self.zset = {r: e for r, e in self.zset.items() if e > now}
            if room in self.zset:
                self.zset[room] = expiry
                return [1, len(self.zset)]
            if len(self.zset) >= max_slots:
                return [0, len(self.zset)]
            self.zset[room] = expiry
            return [1, len(self.zset)]
        if script is capacity.RELEASE:
            removed = 1 if self.zset.pop(str(args[0]), None) is not None else 0
            return [removed, len(self.zset)]
        if script is capacity.EXTEND:
            room, expiry = str(args[0]), int(args[1])
            if room in self.zset:
                self.zset[room] = expiry
                return 1
            return 0
        raise AssertionError("unknown script")


@pytest.fixture
def redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    fake = FakeRedis()
    monkeypatch.setattr(capacity, "get_redis", lambda: fake)
    return fake


def a_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "jwt_secret": "x",
        "worker_secret": "x",
        "livekit_cloud_overflow_enabled": True,
        "livekit_cloud_max_concurrent": 2,
    }
    return Settings(**{**defaults, **overrides})  # type: ignore[arg-type]


async def test_a_slot_is_reserved_and_counted(redis: FakeRedis) -> None:
    result = await capacity.try_reserve(a_settings(), "room-1")
    assert result.reserved is True
    assert result.active_count == 1


async def test_the_same_room_twice_holds_one_slot(redis: FakeRedis) -> None:
    """A candidate reloading the page must not consume a second slot."""
    await capacity.try_reserve(a_settings(), "room-1")
    again = await capacity.try_reserve(a_settings(), "room-1")

    assert again.reserved is True
    assert again.active_count == 1


async def test_the_cap_refuses_the_next_room(redis: FakeRedis) -> None:
    settings = a_settings()
    assert (await capacity.try_reserve(settings, "a")).reserved
    assert (await capacity.try_reserve(settings, "b")).reserved

    third = await capacity.try_reserve(settings, "c")

    assert third.reserved is False
    assert third.active_count == 2


async def test_an_expired_room_does_not_hold_a_slot_forever(redis: FakeRedis) -> None:
    """A worker that dies without releasing must not cost a slot permanently."""
    settings = a_settings()
    await capacity.try_reserve(settings, "abandoned")
    redis.zset["abandoned"] = time.time() - 1

    assert (await capacity.try_reserve(settings, "fresh")).reserved is True
    assert "abandoned" not in redis.zset


async def test_releasing_frees_the_slot(redis: FakeRedis) -> None:
    settings = a_settings()
    await capacity.try_reserve(settings, "room-1")

    assert await capacity.release(settings, "room-1") is True
    assert (await capacity.try_reserve(settings, "other")).active_count == 1


async def test_extending_only_lengthens_a_slot_that_exists(redis: FakeRedis) -> None:
    """A worker in a room nobody reserved is self-hosted, and must not be counted."""
    settings = a_settings()
    assert await capacity.extend(settings, "never-reserved") is False

    await capacity.try_reserve(settings, "room-1")
    before = redis.zset["room-1"]
    assert await capacity.extend(settings, "room-1") is True
    assert redis.zset["room-1"] > before


async def test_redis_being_down_means_self_hosted_not_unlimited(redis: FakeRedis) -> None:
    redis.fail = True

    assert await capacity.slots_free(a_settings(), "room-1") is False


async def test_overflow_disabled_uses_cloud_without_metering(redis: FakeRedis) -> None:
    """Disabled means "do not meter", not "do not use Cloud".

    Reading it the other way would move every Cloud session onto our own
    workers on the next deploy, silently.
    """
    settings = a_settings(livekit_cloud_overflow_enabled=False)

    assert await capacity.slots_free(settings, "room-1") is True
    assert redis.zset == {}, "nothing should be counted when metering is off"
