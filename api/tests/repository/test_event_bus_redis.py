"""The shared pub/sub subscriber against a real Redis (the `seat_redis` fixture)."""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from redis.asyncio import Redis

from app.core import events
from app.core.events import RedisEventBus, SharedSubscriber

URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6380/15")


def connect() -> Redis:
    return Redis.from_url(URL, decode_responses=True, socket_timeout=None)


@pytest_asyncio.fixture
async def bus(seat_redis: Redis) -> AsyncIterator[tuple[RedisEventBus, SharedSubscriber, Redis]]:
    subscriber = SharedSubscriber(connect)
    yield RedisEventBus(seat_redis, subscriber), subscriber, seat_redis
    await subscriber.close()


async def next_message(stream: AsyncIterator[str]) -> str:
    return await asyncio.wait_for(stream.__anext__(), timeout=3)


async def clients(redis: Redis) -> int:
    return len(await redis.client_list())


async def test_fifty_subscriptions_share_one_connection_and_all_hear_a_publish(bus) -> None:  # type: ignore[no-untyped-def]
    event_bus, subscriber, redis = bus
    topic = f"t:{uuid.uuid4().hex}"
    before = await clients(redis)
    managers = [event_bus.subscription([topic]) for _ in range(50)]
    streams = [await m.__aenter__() for m in managers]
    try:
        assert await clients(redis) - before <= 2
        await event_bus.publish(topic, "hello")
        assert [await next_message(s) for s in streams] == ["hello"] * 50
        assert topic in subscriber._topics
    finally:
        for m in managers:
            await m.__aexit__(None, None, None)
    assert subscriber._topics == {}


async def test_a_topic_is_unsubscribed_when_its_last_listener_leaves(bus) -> None:  # type: ignore[no-untyped-def]
    event_bus, subscriber, redis = bus
    topic = f"t:{uuid.uuid4().hex}"
    async with event_bus.subscription([topic]):
        async with event_bus.subscription([topic]):
            pass
        assert topic in subscriber._topics
    assert topic not in subscriber._topics
    for _ in range(20):  # Redis confirms an UNSUBSCRIBE a moment after it is sent
        if await redis.pubsub_channels(topic) == []:
            break
        await asyncio.sleep(0.05)
    assert await redis.pubsub_channels(topic) == []


async def test_a_listener_that_falls_behind_is_ended_and_the_others_are_not(bus) -> None:  # type: ignore[no-untyped-def]
    event_bus, _, _ = bus
    topic = f"t:{uuid.uuid4().hex}"
    async with event_bus.subscription([topic]) as slow, event_bus.subscription([topic]) as quick:
        for n in range(events.LISTENER_QUEUE_SIZE + 1):
            await event_bus.publish(topic, str(n))
            if n < events.LISTENER_QUEUE_SIZE:
                assert await next_message(quick) == str(n)
        await asyncio.sleep(0.2)
        with pytest.raises(StopAsyncIteration):
            await next_message(slow)
        await event_bus.publish(topic, "after")
        assert await next_message(quick) == str(events.LISTENER_QUEUE_SIZE)
        assert await next_message(quick) == "after"


async def test_a_lost_connection_ends_the_streams_and_the_next_subscriber_gets_a_live_one(  # type: ignore[no-untyped-def]
    bus, monkeypatch
) -> None:
    event_bus, subscriber, redis = bus
    monkeypatch.setattr(events, "RECONNECT_BACKOFF_MIN_SECONDS", 0.05)
    topic = f"t:{uuid.uuid4().hex}"
    async with event_bus.subscription([topic]) as stream:
        await redis.execute_command("CLIENT", "KILL", "TYPE", "pubsub")
        with pytest.raises(StopAsyncIteration):
            await next_message(stream)
    for _ in range(40):  # the reader finishes its backoff and stops, nobody being left to serve
        if subscriber._reader is None:
            break
        await asyncio.sleep(0.05)
    async with event_bus.subscription([topic]) as again:
        await event_bus.publish(topic, "back")
        assert await next_message(again) == "back"


async def test_a_stream_opened_while_the_link_is_down_is_ended_at_once(bus, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    event_bus, subscriber, redis = bus
    monkeypatch.setattr(events, "RECONNECT_BACKOFF_MIN_SECONDS", 0.5)
    topic = f"t:{uuid.uuid4().hex}"
    async with event_bus.subscription([topic]) as first:
        await redis.execute_command("CLIENT", "KILL", "TYPE", "pubsub")
        with pytest.raises(StopAsyncIteration):
            await next_message(first)
        async with event_bus.subscription([topic]) as during:
            with pytest.raises(StopAsyncIteration):
                await next_message(during)
        for _ in range(40):  # after the backoff the reader has resubscribed
            if not subscriber._down:
                break
            await asyncio.sleep(0.05)
        async with event_bus.subscription([topic]) as after:
            await event_bus.publish(topic, "live")
            assert await next_message(after) == "live"
