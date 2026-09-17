"""Telling screens that something changed, instead of being asked every 5 seconds.

Two adapters behind one port:

- **Redis pub/sub**, when Redis is configured. A deployment runs more than one
  API replica and a supervisor's stream is almost never on the replica that
  handled the write, so the fan-out has to leave the process. b2c's SSE manager
  is an in-process dictionary of queues and says so in its own log line — with
  a second worker, half the events are delivered to nobody.
- **In-process**, when Redis is off (tests, and local development). Correct for
  one replica, and honest about being no more than that.

Events carry a name and nothing else. Subscribers rebuild the read model from
the database, so a stream cannot show a shape assembled by a writer who knew
less than the reader, a missed event costs a reconnect rather than a wrong
screen, and no user data crosses the bus.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import EventBus
from app.core.redis import get_redis


# Topic names. Functions rather than f-strings at each call site: a publisher
# and a subscriber spelling a topic differently is silence, not an error.
def circuit_topic(circuit_id: object) -> str:
    return f"circuit:{circuit_id}"


def user_topic(user_id: object) -> str:
    return f"user:{user_id}"


PENDING_KEY = "pending_events"


def publish_after_commit(session: AsyncSession, topic: str, name: str) -> None:
    """Queue an event to go out once this request's transaction commits.

    Publishing inline is the bug this exists to prevent: a subscriber woken
    before the commit re-reads the database, sees the old rows, and renders a
    screen that is one event behind for as long as nothing else happens. Held
    on the session rather than in a context variable because every service
    already has the session, and because a buffer keyed on nothing is a buffer
    that leaks across requests.
    """
    session.info.setdefault(PENDING_KEY, []).append((topic, name))


async def flush_pending(session: AsyncSession, bus: EventBus | None = None) -> None:
    """Send what the committed transaction queued. Called by `core.db` only.

    A failure to publish is logged and swallowed: the write is already
    committed, and a screen that updates a few seconds late when it next polls
    or reconnects is better than a request that reports failure for work that
    succeeded.
    """
    pending: list[tuple[str, str]] = session.info.pop(PENDING_KEY, [])
    if not pending:
        return
    target = bus or get_event_bus()
    for topic, name in pending:
        with contextlib.suppress(Exception):
            await target.publish(topic, name)


async def _drain(queue: asyncio.Queue[str]) -> AsyncIterator[str]:
    while True:
        yield await queue.get()


async def _listen(pubsub: object) -> AsyncIterator[str]:
    """Redis messages, one at a time.

    The one-second timeout is not a poll of the database — it is how the client
    hands control back so the connection can be closed when the subscriber goes
    away. Nothing is missed in between: Redis buffers into the subscription.
    """
    while True:
        message = await pubsub.get_message(  # type: ignore[attr-defined]
            ignore_subscribe_messages=True, timeout=1.0
        )
        if message is None:
            continue
        yield str(message["data"])


class InProcessEventBus:
    """One process, one set of queues. The fallback when Redis is off."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[str]]] = {}

    async def publish(self, topic: str, name: str) -> None:
        for queue in set(self._subscribers.get(topic, ())):
            queue.put_nowait(name)

    @contextlib.asynccontextmanager
    async def subscription(self, topics: Sequence[str]) -> AsyncIterator[AsyncIterator[str]]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        for topic in topics:
            self._subscribers.setdefault(topic, set()).add(queue)
        try:
            yield _drain(queue)
        finally:
            for topic in topics:
                listeners = self._subscribers.get(topic)
                if listeners is not None:
                    listeners.discard(queue)
                    if not listeners:
                        self._subscribers.pop(topic, None)


class RedisEventBus:
    """Pub/sub, so any replica can tell a stream held by any other."""

    def __init__(self, redis: object) -> None:
        self._redis = redis

    async def publish(self, topic: str, name: str) -> None:
        await self._redis.publish(topic, name)  # type: ignore[attr-defined]

    @contextlib.asynccontextmanager
    async def subscription(self, topics: Sequence[str]) -> AsyncIterator[AsyncIterator[str]]:
        pubsub = self._redis.pubsub()  # type: ignore[attr-defined]
        await pubsub.subscribe(*topics)
        try:
            yield _listen(pubsub)
        finally:
            with contextlib.suppress(Exception):
                await pubsub.unsubscribe(*topics)
            with contextlib.suppress(Exception):
                await pubsub.aclose()


_in_process = InProcessEventBus()


def get_event_bus() -> EventBus:
    """Redis when it is configured, one process when it is not."""
    redis = get_redis()
    return _in_process if redis is None else RedisEventBus(redis)
