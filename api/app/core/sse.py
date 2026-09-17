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
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass

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


class StreamFinished(Exception):
    """Raised by a snapshot to say this stream has nothing further to send.

    The circuit ended; the result was acknowledged. The last snapshot is sent
    first, then the stream closes, so a client is not left holding a connection
    to something that is over.
    """


@dataclass(frozen=True)
class Snapshot:
    """What to send, and whether there will ever be anything after it.

    `final` exists so a stream can say goodbye properly: an ended circuit is
    sent one last time — the console needs that last state to render — and then
    the connection closes, rather than being held open all night by a browser
    left on the page.
    """

    data: str
    final: bool = False


def frame(event: str, data: str) -> str:
    """One SSE frame. `data` is already-encoded JSON.

    Newlines inside the payload are re-prefixed rather than escaped: a bare
    newline in `data:` silently ends the frame, and the client sees half an
    object with no error anywhere.
    """
    body = "\n".join(f"data: {line}" for line in data.split("\n"))
    return f"event: {event}\n{body}\n\n"


async def event_stream(
    *,
    topics: Sequence[str],
    snapshot: Callable[[], Awaitable[Snapshot]],
    bus: EventBus,
    heartbeat_seconds: float = HEARTBEAT_SECONDS,
) -> AsyncIterator[str]:
    """Send the current state, then send it again whenever something happens.

    The client gets `connected`, then a `snapshot` immediately — so a stream is
    a complete replacement for the poll it removes, not an addition to it.
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
