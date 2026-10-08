"""The read models, delivered when they change instead of when asked.

Each stream is the streaming form of a `GET` that already exists and sends exactly what
that route returns, so a client keeps one decoder and one set of types either way.

Every snapshot opens its own short transaction — a connection held for the life of a
supervisor's tab is an idle transaction that pins a pooled connection and blocks vacuum for
the whole examination.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.db import SessionOpener
from app.core.events import circuit_topic, org_topic, user_topic
from app.core.ports import Clock, EventBus
from app.core.sse import Snapshot, StreamFinished, event_stream
from app.features.dashboard import service_console, service_live, service_trainee
from app.features.dashboard.errors import CircuitNotFound
from app.features.tenancy import service as tenancy


async def _still_a_member(session: AsyncSession, principal: Principal, org_id: uuid.UUID) -> None:
    """End the stream once the person is no longer in the organisation.

    A token lives up to fifteen minutes after a removal; a stream opened with it would otherwise
    keep pushing candidate names for as long as the tab stays open. A role change is not checked
    here: it takes effect on the next request.
    """
    if principal.is_platform_admin:
        return
    if not await tenancy.holds_live_membership(session, user_id=principal.user_id, org_id=org_id):
        raise StreamFinished


def console_stream(
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    principal: Principal,
    *,
    bus: EventBus,
    open_session: SessionOpener,
    clock: Clock,
) -> AsyncIterator[str]:
    """The supervisor's console, pushed.

    A circuit that has ended is sent once more and then the stream closes.
    """

    async def snapshot() -> Snapshot:
        """One frame: the console as it stands right now, in its own short transaction."""
        async with open_session() as session:
            await _still_a_member(session, principal, org_id)
            try:
                console = await service_console.build_console(session, org_id, circuit_id, now=clock.now())
            except CircuitNotFound:
                # Deleted, or never this org's. Closing says so in the one way
                # a stream can; the client re-reads the route for the status.
                raise StreamFinished from None
        # An ended circuit gets one last snapshot and then the stream closes.
        return Snapshot(console.model_dump_json(), final=console.circuit.ended_at is not None)

    # A snapshot on every heartbeat: with the worker down nothing is announced, and a
    # snapshot is what catches a due circuit up (S-7).
    return event_stream(
        topics=[circuit_topic(circuit_id)], snapshot=snapshot, bus=bus, snapshot_on_heartbeat=True
    )


def my_sittings_stream(
    principal: Principal,
    *,
    bus: EventBus,
    open_session: SessionOpener,
    clock: Clock,
    org_slug: str | None = None,
) -> AsyncIterator[str]:
    """The trainee portal, pushed.

    Subscribed by user rather than by circuit: a trainee may be rostered onto several at
    once, and every circuit change tells the people on it as well as the console.
    """

    async def snapshot() -> Snapshot:
        """One frame: this trainee's whole portal, as it stands right now."""
        async with open_session() as session:
            mine = await service_trainee.my_sittings(
                session, principal.user_id, now=clock.now(), org_slug=org_slug
            )
        # Never final: a trainee's portal outlives any one sitting.
        return Snapshot(mine.model_dump_json())

    return event_stream(topics=[user_topic(principal.user_id)], snapshot=snapshot, bus=bus)


def live_board_stream(
    org_id: uuid.UUID, principal: Principal, *, bus: EventBus, open_session: SessionOpener, clock: Clock
) -> AsyncIterator[str]:
    """The exam-day board, pushed.

    Subscribed to the organisation rather than to each circuit, so an admin watching several
    candidates holds one stream and does not miss a new circuit starting. Never final.
    """

    async def snapshot() -> Snapshot:
        """One frame: every circuit this organisation has running, as it stands right now."""
        async with open_session() as session:
            await _still_a_member(session, principal, org_id)
            board = await service_live.build_live_board(session, org_id, now=clock.now())
        return Snapshot(board.model_dump_json())

    return event_stream(topics=[org_topic(org_id)], snapshot=snapshot, bus=bus, snapshot_on_heartbeat=True)
