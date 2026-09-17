"""The frame format and the loop, without a database or a network.

These are the parts every hand-rolled stream gets wrong: a payload containing a
newline, a connection that goes quiet and is closed by a proxy, and a stream
that never ends.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

from app.core.events import InProcessEventBus
from app.core.sse import Snapshot, StreamFinished, event_stream, frame


def test_a_frame_is_an_event_and_a_data_line() -> None:
    assert frame("snapshot", '{"a":1}') == 'event: snapshot\ndata: {"a":1}\n\n'


def test_a_payload_with_newlines_stays_one_frame() -> None:
    """A bare newline inside `data:` ends the frame, and the client sees half an object."""
    assert frame("snapshot", '{\n  "a": 1\n}') == 'event: snapshot\ndata: {\ndata:   "a": 1\ndata: }\n\n'


class OneEventBus:
    """Publishes a single event, then goes quiet forever."""

    def __init__(self, name: str = "changed") -> None:
        self._name = name
        self.topics: list[str] = []
        self.subscribed = False

    async def publish(self, topic: str, name: str) -> None:  # pragma: no cover - not used
        raise NotImplementedError

    @asynccontextmanager
    async def subscription(self, topics: Sequence[str]) -> AsyncIterator[AsyncIterator[str]]:
        self.topics = list(topics)
        self.subscribed = True
        yield self._one()

    async def _one(self) -> AsyncIterator[str]:
        yield self._name
        await asyncio.Event().wait()  # never fires: the stream must heartbeat instead


async def test_a_stream_opens_with_the_current_state() -> None:
    """A stream replaces the poll it removes, so it starts by sending everything."""
    stream = event_stream(
        topics=["circuit:1"],
        snapshot=lambda: _snapshot('{"n":1}'),
        bus=OneEventBus(),
    )
    frames = [await anext(stream), await anext(stream)]
    assert frames[0] == "event: connected\ndata: {}\n\n"
    assert frames[1] == 'event: snapshot\ndata: {"n":1}\n\n'
    await stream.aclose()


async def test_an_event_sends_a_fresh_snapshot() -> None:
    counter = {"n": 0}

    async def snapshot() -> Snapshot:
        counter["n"] += 1
        return Snapshot(f'{{"n":{counter["n"]}}}')

    bus = OneEventBus()
    stream = event_stream(topics=["circuit:1"], snapshot=snapshot, bus=bus)
    await anext(stream)  # connected
    assert await anext(stream) == 'event: snapshot\ndata: {"n":1}\n\n'
    assert await anext(stream) == 'event: snapshot\ndata: {"n":2}\n\n'
    assert bus.topics == ["circuit:1"]
    await stream.aclose()


async def test_a_quiet_stream_sends_a_heartbeat() -> None:
    """Proxies close an idle connection at 30 to 60 seconds, silently."""
    bus = InProcessEventBus()
    stream = event_stream(
        topics=["circuit:1"],
        snapshot=lambda: _snapshot("{}"),
        bus=bus,
        heartbeat_seconds=0.01,
    )
    await anext(stream)  # connected
    await anext(stream)  # snapshot
    assert await anext(stream) == "event: ping\ndata: {}\n\n"
    await stream.aclose()


async def test_a_final_snapshot_closes_the_stream() -> None:
    """The circuit ended: send that state, then stop holding the connection."""
    stream = event_stream(
        topics=["circuit:1"],
        snapshot=lambda: _snapshot('{"ended":true}', final=True),
        bus=OneEventBus(),
    )
    assert [f async for f in stream] == [
        "event: connected\ndata: {}\n\n",
        'event: snapshot\ndata: {"ended":true}\n\n',
    ]


async def test_a_stream_with_nothing_to_show_closes_immediately() -> None:
    async def gone() -> Snapshot:
        raise StreamFinished

    stream = event_stream(topics=["circuit:1"], snapshot=gone, bus=OneEventBus())
    assert [f async for f in stream] == ["event: connected\ndata: {}\n\n"]


async def test_the_in_process_bus_delivers_to_every_subscriber_of_a_topic() -> None:
    bus = InProcessEventBus()
    async with bus.subscription(["circuit:1"]) as first, bus.subscription(["circuit:1"]) as second:
        await bus.publish("circuit:1", "circuit.started")
        assert await asyncio.wait_for(anext(first), timeout=1) == "circuit.started"
        assert await asyncio.wait_for(anext(second), timeout=1) == "circuit.started"


async def test_an_event_published_before_the_first_read_is_still_delivered() -> None:
    """Entering the subscription is what subscribes, not the first read.

    The stream takes its snapshot after entering and before reading, and an
    event in that window has to survive — otherwise the screen it was about
    stays wrong until something else changes.
    """
    bus = InProcessEventBus()
    async with bus.subscription(["circuit:1"]) as events:
        await bus.publish("circuit:1", "circuit.started")
        assert await asyncio.wait_for(anext(events), timeout=1) == "circuit.started"


async def test_the_in_process_bus_forgets_a_subscriber_that_goes_away() -> None:
    """Otherwise a queue per abandoned tab accumulates for the life of the process."""
    bus = InProcessEventBus()
    async with bus.subscription(["circuit:1"]):
        await bus.publish("circuit:1", "x")
    assert bus._subscribers == {}


async def test_a_stream_subscribes_before_it_reads_anything() -> None:
    bus = OneEventBus()
    stream = event_stream(topics=["circuit:1"], snapshot=lambda: _snapshot("{}"), bus=bus)
    await anext(stream)  # connected
    await anext(stream)  # snapshot
    assert bus.subscribed
    await stream.aclose()


async def test_a_topic_nobody_watches_is_not_an_error() -> None:
    await InProcessEventBus().publish("circuit:nobody", "circuit.started")


async def _snapshot(data: str, *, final: bool = False) -> Snapshot:
    return Snapshot(data, final=final)
