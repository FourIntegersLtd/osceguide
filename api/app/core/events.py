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
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from typing import Any

from redis.asyncio import Redis
from redis.asyncio.client import PubSub
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.ports import EventBus
from app.core.redis import get_redis, new_subscriber_client

log = get_logger(__name__)


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


AFTER_COMMIT_KEY = "after_commit_calls"


def run_after_commit(session: AsyncSession, call: Callable[[], Awaitable[None]]) -> None:
    """Queue best-effort work on another system (a LiveKit call) to run once this transaction commits.

    Like `publish_after_commit`: a rolled-back request never runs it, and it never runs under the
    row lock a request holds. A failure is the call's own to handle; it cannot fail the request.
    """
    session.info.setdefault(AFTER_COMMIT_KEY, []).append(call)


async def flush_after_commit_calls(session: AsyncSession) -> None:
    """Run what `run_after_commit` queued. Called by `core.db` only; a rollback never calls it."""
    calls: list[Callable[[], Awaitable[None]]] = session.info.pop(AFTER_COMMIT_KEY, [])
    for call in calls:
        with contextlib.suppress(Exception):
            await call()


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


# One stream may fall this far behind before it is cut loose. A browser that
# is slower than the bus is better off reconnecting to a fresh snapshot than
# holding the whole process's memory for a backlog it will rebuild anyway.
LISTENER_QUEUE_SIZE = 100
CONFIRM_TIMEOUT_SECONDS = 2.0
RECONNECT_BACKOFF_MIN_SECONDS = 1.0
RECONNECT_BACKOFF_MAX_SECONDS = 30.0


class _Listener:
    """One subscription's bounded inbox. `None` in it means the stream must end."""

    def __init__(self) -> None:
        self.queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=LISTENER_QUEUE_SIZE)
        self.ended = False

    def offer(self, message: str) -> None:
        """Queue a message, or cut this stream loose when it is too far behind."""
        if self.ended:
            return
        try:
            self.queue.put_nowait(message)
        except asyncio.QueueFull:
            self.end()

    def end(self) -> None:
        """Drop what is queued and end the stream; the browser reconnects to a snapshot plus `resync`."""
        if self.ended:
            return
        self.ended = True
        while not self.queue.empty():
            self.queue.get_nowait()
        self.queue.put_nowait(None)

    async def stream(self) -> AsyncIterator[str]:
        """Yield messages until the stream is ended."""
        while (message := await self.queue.get()) is not None:
            yield message


class SharedSubscriber:
    """One Redis pub/sub connection and one reader task for the whole process.

    A connection per open stream spends one Redis client slot per browser tab
    and a task each to read it. Here every stream holds a bounded queue and
    the single reader hands each message to the queues of that topic.
    Subscribes on a topic's first listener and unsubscribes on its last.

    When the connection drops, or a queue overflows, the affected streams are
    ended rather than patched: events published while the link was down are
    gone, and a reconnecting stream re-reads the read model anyway.
    """

    def __init__(self, connect: Callable[[], Redis]) -> None:
        self._connect = connect
        self._topics: dict[str, set[_Listener]] = {}
        self._client: Redis | None = None
        self._pubsub: PubSub | None = None
        self._reader: asyncio.Task[None] | None = None
        # Redis confirms a SUBSCRIBE some moments after it is sent. A publish landing in
        # that gap reaches nobody, so `subscribe` waits for the confirmation.
        self._confirmations: dict[str, asyncio.Future[None]] = {}
        # True from a lost connection until the reader has resubscribed. A stream opened in
        # that gap would hear nothing, so it is ended at once and its browser retries.
        self._down = False

    def _ensure_pubsub(self) -> PubSub:
        """The live Redis subscription, opened on first use and again after a drop."""
        if self._pubsub is None:
            self._client = self._connect()
            self._pubsub = self._client.pubsub()
        return self._pubsub

    async def subscribe(self, topics: Sequence[str]) -> _Listener:
        """Register a listener against these topics; returns once Redis has them."""
        listener = _Listener()
        if self._down:
            listener.end()
            return listener
        fresh = [topic for topic in dict.fromkeys(topics) if topic not in self._topics]
        for topic in topics:
            self._topics.setdefault(topic, set()).add(listener)
        try:
            loop = asyncio.get_running_loop()
            for topic in fresh:
                self._confirmations[topic] = loop.create_future()
            if fresh:
                await self._ensure_pubsub().subscribe(*fresh)
            self._ensure_reader()
            waiting = [self._confirmations[name] for name in topics if name in self._confirmations]
            if waiting:
                await asyncio.wait_for(asyncio.gather(*waiting), timeout=CONFIRM_TIMEOUT_SECONDS)
        except BaseException:
            await self.unsubscribe(topics, listener)
            raise
        return listener

    async def unsubscribe(self, topics: Sequence[str], listener: _Listener) -> None:
        """Remove the listener; a topic nobody else listens to is unsubscribed on Redis."""
        gone = []
        for topic in topics:
            listeners = self._topics.get(topic)
            if listeners is None:
                continue
            listeners.discard(listener)
            if not listeners:
                del self._topics[topic]
                gone.append(topic)
                unconfirmed = self._confirmations.pop(topic, None)
                if unconfirmed is not None:
                    unconfirmed.cancel()
        if gone and self._pubsub is not None:
            with contextlib.suppress(Exception):
                await self._pubsub.unsubscribe(*gone)

    def _ensure_reader(self) -> None:
        """Start the one task that reads Redis, unless it is already running."""
        if self._reader is None:
            self._reader = asyncio.create_task(self._read())

    def _dispatch(self, topic: str, message: str) -> None:
        """Hand a message to every stream listening to its topic."""
        for listener in tuple(self._topics.get(topic, ())):
            listener.offer(message)

    def _end_all(self) -> None:
        """End every open stream, so each browser reconnects to a fresh snapshot."""
        for listeners in self._topics.values():
            for listener in listeners:
                listener.end()

    def _detach(self) -> Redis | None:
        """Forget the connection at once and hand it back to be closed (closing awaits)."""
        client, self._client, self._pubsub = self._client, None, None
        return client

    def _handle(self, message: dict[str, Any]) -> None:
        """Route one pub/sub message: a publish to its streams, a subscribe to its waiting caller."""
        if message["type"] == "message":
            self._dispatch(str(message["channel"]), str(message["data"]))
        elif message["type"] == "subscribe":
            confirmed = self._confirmations.pop(str(message["channel"]), None)
            if confirmed is not None and not confirmed.done():
                confirmed.set_result(None)

    async def _close_detached(self) -> None:
        """Forget the connection and close it, ignoring a link that is already gone."""
        client = self._detach()
        if client is not None:
            with contextlib.suppress(Exception):
                await client.aclose()

    async def _read(self) -> None:
        """Read until nobody listens; on a lost connection end the streams, back off, resubscribe."""
        backoff = RECONNECT_BACKOFF_MIN_SECONDS
        try:
            while self._topics:
                try:
                    pubsub = self._ensure_pubsub()
                    if self._down:
                        await pubsub.subscribe(*self._topics)
                        self._down = False
                    async for message in pubsub.listen():
                        backoff = RECONNECT_BACKOFF_MIN_SECONDS
                        self._handle(message)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001 - any failure of the link is a reconnect
                    log.warning("event bus connection lost", error=repr(exc))
                if not self._topics:
                    break
                self._down = True
                self._end_all()
                await self._close_detached()
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, RECONNECT_BACKOFF_MAX_SECONDS)
        finally:
            # Atomic with the loop test above: a subscriber arriving from now on starts a new reader.
            self._reader = None
            self._down = False
            await self._close_detached()

    async def close(self) -> None:
        """Stop reading and release the connection. Called at shutdown."""
        reader = self._reader
        if reader is not None:
            reader.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await reader
        await self._close_detached()


class RedisEventBus:
    """Pub/sub, so any replica can tell a stream held by any other."""

    def __init__(self, redis: object, subscriber: SharedSubscriber | None = None) -> None:
        self._redis = redis
        self._subscriber = subscriber

    async def publish(self, topic: str, name: str) -> None:
        await self._redis.publish(topic, name)  # type: ignore[attr-defined]

    @contextlib.asynccontextmanager
    async def subscription(self, topics: Sequence[str]) -> AsyncIterator[AsyncIterator[str]]:
        """Subscribe to these topics on Redis for as long as the caller holds the subscription open."""
        subscriber = self._subscriber or get_shared_subscriber()
        listener = await subscriber.subscribe(topics)
        try:
            yield listener.stream()
        finally:
            await subscriber.unsubscribe(topics, listener)


_shared: SharedSubscriber | None = None


def get_shared_subscriber() -> SharedSubscriber:
    """This process's one subscriber, with a Redis client of its own (`core.redis.new_subscriber_client`)."""
    global _shared
    if _shared is None:
        _shared = SharedSubscriber(new_subscriber_client)
    return _shared


async def close_event_bus() -> None:
    """Release the shared subscription. Called at shutdown, before `close_redis`."""
    global _shared
    if _shared is not None:
        await _shared.close()
    _shared = None


_in_process = InProcessEventBus()


def get_event_bus() -> EventBus:
    """Redis when it is configured, one process when it is not."""
    redis = get_redis()
    return _in_process if redis is None else RedisEventBus(redis)
