"""Telling screens that something changed, instead of being asked every 5 seconds.

Two adapters behind one port:

- **Redis pub/sub**, when Redis is configured. A deployment runs more than one
  API replica and a supervisor's stream is almost never on the replica that
  handled the write, so the fan-out has to leave the process.
- **In-process**, when Redis is off (tests, and local development). Correct
  for one replica, and honest about being no more than that.

Events carry a name and, optionally, a small id-only payload. Most subscribers
still just rebuild the read model from the database on any wakeup, so a
missed event costs a reconnect rather than a wrong screen. `/me/events`
(`app.features.identity.router_me`) is the one subscriber that reads the
payload, because it multiplexes many kinds of change onto a single
connection and a screen needs the id to know whether an event is about it.
No user data beyond ids crosses the bus.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator, Mapping, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import EventBus
from app.core.redis import get_redis


# Topic names. Functions rather than f-strings at each call site: a publisher
# and a subscriber spelling a topic differently is silence, not an error.
def circuit_topic(circuit_id: object) -> str:
    return f"circuit:{circuit_id}"


def user_topic(user_id: object) -> str:
    return f"user:{user_id}"


def voice_queue_topic() -> str:
    """Everyone waiting for a voice seat. Published when one frees up."""
    return "voice:queue"


def org_topic(org_id: object) -> str:
    """One subscription for everything happening inside an organisation.

    The exam-day board watches this instead of subscribing per circuit, so it
    does not miss a new circuit starting.
    """
    return f"org:{org_id}"


PENDING_KEY = "pending_events"


def encode_message(name: str, payload: Mapping[str, object] | None = None) -> str:
    """The wire form of one event: its name, and a small id-only payload.

    Always JSON, even when `payload` is empty, so every subscriber decodes the
    same shape. A subscriber that only wants a wakeup (most of them: they
    rebuild their read model from the database) can go on ignoring the
    content; `/me/events` is the one that reads `data` back out.
    """
    return json.dumps({"event": name, "data": dict(payload or {})})


def publish_after_commit(
    session: AsyncSession, topic: str, name: str, payload: Mapping[str, object] | None = None
) -> None:
    """Queue an event to go out once this request's transaction commits.

    Publishing inline would wake a subscriber before the commit, which
    re-reads the database, sees the old rows, and renders a stale screen.
    Held on the session, not a context variable, so the buffer cannot leak
    across requests. `payload` is a handful of ids at most — never user data —
    because it crosses process boundaries over Redis in production.
    """
    session.info.setdefault(PENDING_KEY, []).append((topic, name, dict(payload or {})))


async def flush_pending(session: AsyncSession, bus: EventBus | None = None) -> None:
    """Send what the committed transaction queued. Called by `core.db` only.

    A failure to publish is swallowed: the write is already committed, and a
    screen updating late on reconnect is better than reporting failure for
    work that succeeded.
    """
    pending: list[tuple[str, str, dict[str, object]]] = session.info.pop(PENDING_KEY, [])
    if not pending:
        return
    target = bus or get_event_bus()
    for topic, name, payload in pending:
        with contextlib.suppress(Exception):
            await target.publish(topic, encode_message(name, payload))


async def _drain(queue: asyncio.Queue[str]) -> AsyncIterator[str]:
    """Yield whatever this subscriber's queue receives, forever."""
    while True:
        yield await queue.get()


async def _listen(pubsub: object) -> AsyncIterator[str]:
    """Redis messages, one at a time.

    The one-second timeout is how the client hands control back so the
    connection can be closed when the subscriber goes away — not a poll;
    Redis buffers into the subscription so nothing is missed in between.
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
        """Wake every current subscriber to `topic` with `name`."""
        for queue in set(self._subscribers.get(topic, ())):
            queue.put_nowait(name)

    @contextlib.asynccontextmanager
    async def subscription(self, topics: Sequence[str]) -> AsyncIterator[AsyncIterator[str]]:
        """Register a queue against these topics for as long as the caller holds it open."""
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
        """Subscribe to these topics on Redis for as long as the caller holds the subscription open."""
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
