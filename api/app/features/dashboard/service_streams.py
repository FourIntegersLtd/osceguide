"""The read models, delivered when they change instead of when asked.

Each stream is the streaming form of a `GET` that already exists, and sends
exactly what that route returns. That is the point: a client keeps one decoder,
one set of types and one mental model, and a stream can be swapped back for the
poll it replaced without changing a line of rendering code.

Every snapshot opens its own short transaction (`core.db.stream_session`) — a
connection held for the life of a supervisor's tab is an idle transaction that
pins a pooled connection and blocks vacuum for the whole examination.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Mapping

from app.core.auth import Principal
from app.core.db import SessionOpener
from app.core.events import circuit_topic, user_topic
from app.core.ports import EventBus
from app.core.sse import Snapshot, StreamFinished, event_stream
from app.features.dashboard import service_org, service_trainee
from app.features.dashboard.errors import CircuitNotFound


def console_stream(
    org_id: uuid.UUID, circuit_id: uuid.UUID, *, bus: EventBus, open_session: SessionOpener
) -> AsyncIterator[str]:
    """The supervisor's console, pushed. Replaces an eight-second poll.

    A circuit that has been ended is sent once more and then the stream closes:
    there is nothing further to say about it, and a browser left on the page
    should not hold a connection open all night waiting.
    """

    async def snapshot() -> Snapshot:
        async with open_session() as session:
            try:
                console = await service_org.build_console(session, org_id, circuit_id)
            except CircuitNotFound:
                # Deleted, or never this org's. Closing says so in the one way
                # a stream can; the client re-reads the route for the status.
                raise StreamFinished from None
        # An ended circuit gets one last snapshot and then the stream closes.
        return Snapshot(console.model_dump_json(), final=console.circuit.ended_at is not None)

    return event_stream(topics=[circuit_topic(circuit_id)], snapshot=snapshot, bus=bus)


def my_sittings_stream(
    principal: Principal, *, bus: EventBus, open_session: SessionOpener
) -> AsyncIterator[str]:
    """The trainee portal, pushed. Replaces a five-second poll of two lists.

    Subscribed by user rather than by circuit: a trainee may be rostered onto
    several at once, and is not allowed to read a circuit directly. Every
    circuit change tells the people on it as well as the console, which is what
    makes one subscription enough.
    """
    org_slugs: Mapping[uuid.UUID, str] = {m.org_id: m.org_slug for m in principal.memberships}

    async def snapshot() -> Snapshot:
        async with open_session() as session:
            mine = await service_trainee.my_sittings(session, principal.user_id, org_slugs=org_slugs)
        # Never final: a trainee's portal outlives any one sitting.
        return Snapshot(mine.model_dump_json())

    return event_stream(topics=[user_topic(principal.user_id)], snapshot=snapshot, bus=bus)
