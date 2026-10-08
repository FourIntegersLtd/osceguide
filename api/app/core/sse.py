"""Server-sent events: the frames, the heartbeat, and the loop that joins them.

One stream shape for the whole API, because the interesting parts are the ones
every stream gets wrong on its own.

- **A snapshot, never a diff.** Each frame carries the same read model the
  equivalent `GET` returns, rebuilt from the database. A client that missed an
  event, reconnected, or opened a second tab is correct immediately, and there
  is no second assembly of the same screen to drift from the first.
- **A fresh, short transaction per snapshot.** A stream lives for minutes; a
  request-scoped session held open for that long is an idle transaction pinning
  a connection and blocking vacuum.
- **A heartbeat.** Proxies close an idle connection at 30 to 60 seconds, and a
  silent close looks to a browser like a working stream with nothing happening.
- **`X-Accel-Buffering: no`.** Without it nginx buffers the whole response and
  the client receives nothing until the stream ends, which is never.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable, Sequence
from dataclasses import dataclass

from app.core.errors import AppError
from app.core.ports import EventBus

HEARTBEAT_SECONDS = 25.0

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    # nginx and several CDNs buffer a response body by default, which turns a
    # live stream into one long silence.
    "X-Accel-Buffering": "no",
}

MEDIA_TYPE = "text/event-stream"


# One account holds at most this many live streams *per worker process*, not across the fleet (the
# count lives in this process): a tab per device and a few screens each is normal, a runaway client
# reconnecting without end is not (S-27).
MAX_STREAMS_PER_ACCOUNT = 10
_open_streams: dict[uuid.UUID, int] = {}


class TooManyStreams(AppError):
    """The account already holds as many live streams as it may."""

    status = 429
    code = "too_many_streams"
    default_message = "Too many live connections are open for this account. Close another tab and try again."


def _capped(owner: uuid.UUID, stream: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
    """Refuse a new stream for an account already at its cap, else count it while it runs.

    Called when the route builds the stream, before any bytes are sent, so the refusal is an
    ordinary 429 and not a connection that opens and dies. A stream counts from its first frame
    to its close, so one that never starts holds no place.
    """
    if _open_streams.get(owner, 0) >= MAX_STREAMS_PER_ACCOUNT:
        raise TooManyStreams

    async def counted() -> AsyncGenerator[str, None]:
        """Pass every frame through, holding one of the account's places until the stream closes."""
        _open_streams[owner] = _open_streams.get(owner, 0) + 1
        try:
            async for item in stream:
                yield item
        finally:
            _open_streams[owner] -= 1
            if _open_streams[owner] <= 0:
                del _open_streams[owner]
            await stream.aclose()

    return counted()


class StreamFinished(Exception):
    """Raised by a snapshot to say this stream has nothing further to send.

    The last snapshot is sent first, then the stream closes, so a client is
    not left holding a connection to something that is over.
    """


@dataclass(frozen=True)
class Snapshot:
    """What to send, and whether there will ever be anything after it.

    `final` exists so a stream can say goodbye properly: an ended circuit is
    sent one last time, then the connection closes, rather than being held
    open all night by a browser left on the page.
    """

    data: str
    final: bool = False


def frame(event: str, payload: str) -> str:
    """One SSE frame. `payload` is already-encoded JSON.

    Newlines inside the payload are re-prefixed rather than escaped: a bare
    newline in `data:` silently ends the frame, and the client sees half an
    object with no error anywhere.
    """
    body = "\n".join(f"data: {line}" for line in payload.split("\n"))
    return f"event: {event}\n{body}\n\n"


def event_stream(
    *,
    topics: Sequence[str],
    snapshot: Callable[[], Awaitable[Snapshot]],
    bus: EventBus,
    heartbeat_seconds: float = HEARTBEAT_SECONDS,
    snapshot_on_heartbeat: bool = False,
    owner: uuid.UUID | None = None,
) -> AsyncGenerator[str, None]:
    """The stream below, counted against `owner`'s cap when one is named.

    An account's stream passes its `owner`: a new stream beyond `MAX_STREAMS_PER_ACCOUNT` is refused
    here, when the route builds it and before any bytes are sent, so the refusal is an ordinary 429
    and not a connection that opens and dies. A stream counts from its first frame to its close.
    A platform-wide stream with no owner is not capped.
    """
    stream = _event_stream(
        topics=topics,
        snapshot=snapshot,
        bus=bus,
        heartbeat_seconds=heartbeat_seconds,
        snapshot_on_heartbeat=snapshot_on_heartbeat,
    )
    return stream if owner is None else _capped(owner, stream)


async def _event_stream(
    *,
    topics: Sequence[str],
    snapshot: Callable[[], Awaitable[Snapshot]],
    bus: EventBus,
    heartbeat_seconds: float,
    snapshot_on_heartbeat: bool,
) -> AsyncGenerator[str, None]:
    """Send the current state, then send it again whenever something happens.

    The client gets `connected`, then a `snapshot` immediately — so a stream is
    a complete replacement for the poll it removes, not an addition to it.

    `snapshot_on_heartbeat` sends a snapshot where a ping would go, for a read
    model that also changes with nobody announcing it — a seat whose expiry
    lapses — and whose reads are cheap. The client still only listens.
    """
    yield frame("connected", "{}")

    # Subscribed before the first snapshot is read, never after. An event that
    # lands in between would otherwise reach nobody, and the screen it was
    # about would stay wrong until something else happened to change it.
    async with bus.subscription(list(topics)) as events:
        try:
            first = await snapshot()
        except StreamFinished:
            return
        yield frame("snapshot", first.data)
        if first.final:
            return

        # The subscription is drained by a task rather than awaited directly. A
        # heartbeat means giving up on the wait, and cancelling `__anext__` on
        # an async generator leaves that generator unusable — the next wait
        # either raises "already running" or blocks forever, which is a stream
        # that looks alive and has stopped. Cancelling a queue read is safe.
        queued: asyncio.Queue[str] = asyncio.Queue()

        async def pump() -> None:
            """Move every event off the subscription and onto the queue this loop reads."""
            async for name in events:
                await queued.put(name)

        pumping = asyncio.create_task(pump())
        try:
            while True:
                try:
                    await asyncio.wait_for(queued.get(), timeout=heartbeat_seconds)
                except TimeoutError:
                    if pumping.done():
                        return
                    if not snapshot_on_heartbeat:
                        yield frame("ping", "{}")
                        continue

                # Several changes in the same instant are one snapshot: a
                # supervisor switching turns twice quickly should not queue two
                # renders of the same final state.
                while not queued.empty():
                    queued.get_nowait()

                try:
                    current = await snapshot()
                except StreamFinished:
                    return
                yield frame("snapshot", current.data)
                if current.final:
                    return
        finally:
            pumping.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await pumping


def _decode_message(raw: str) -> tuple[str, str]:
    """Split one bus message into its event name and JSON payload.

    `raw` is whatever `app.core.events.encode_message` produced: a JSON object
    with `event` and `data`. Anything else (a message from before this shape
    existed, or a stray publish elsewhere) is treated as an unnamed change
    with no payload, rather than breaking the stream.
    """
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return raw, "{}"
    if isinstance(parsed, dict) and "event" in parsed:
        return str(parsed["event"]), json.dumps(parsed.get("data") or {})
    return raw, "{}"


def fan_in_stream(
    *,
    topics: Sequence[str],
    bus: EventBus,
    heartbeat_seconds: float = HEARTBEAT_SECONDS,
    owner: uuid.UUID | None = None,
) -> AsyncGenerator[str, None]:
    """The stream below, counted against `owner`'s cap when one is named (see `event_stream`)."""
    stream = _fan_in_stream(topics=topics, bus=bus, heartbeat_seconds=heartbeat_seconds)
    return stream if owner is None else _capped(owner, stream)


async def _fan_in_stream(
    *, topics: Sequence[str], bus: EventBus, heartbeat_seconds: float
) -> AsyncGenerator[str, None]:
    """Forward every named event published on `topics`, as it arrives.

    Unlike `event_stream`, there is no single read model to snapshot: this is
    `/me/events`, one connection carrying many kinds of change (an attempt
    marked, a peer session updated, a CV read), each named and carrying just
    enough of a payload — an id — for a screen to tell whether it is the one
    being talked about. A screen that cares still re-reads its own resource;
    this only tells it when to. Never final: a person's own stream outlives
    any one thing that happened on it.
    """
    yield frame("connected", "{}")
    async with bus.subscription(list(topics)) as events:
        queued: asyncio.Queue[str] = asyncio.Queue()

        async def pump() -> None:
            """Move every raw message off the subscription and onto the queue this loop reads."""
            async for raw in events:
                await queued.put(raw)

        pumping = asyncio.create_task(pump())
        try:
            while True:
                try:
                    raw = await asyncio.wait_for(queued.get(), timeout=heartbeat_seconds)
                except TimeoutError:
                    if pumping.done():
                        return
                    yield frame("ping", "{}")
                    continue
                name, payload = _decode_message(raw)
                yield frame(name, payload)
        finally:
            pumping.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await pumping
