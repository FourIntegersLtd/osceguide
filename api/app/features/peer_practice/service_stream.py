"""Telling somebody in the queue that they have been matched, over SSE rather
than polling: the person is sitting and staring at the screen, and the whole
feature is how quickly they get into a room with somebody.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from app.core.db import SessionOpener
from app.core.events import user_topic
from app.core.ports import EventBus
from app.core.sse import Snapshot, StreamFinished, event_stream
from app.features.peer_practice import errors, service

WAITING = "waiting"


def queue_stream(
    entry_id: uuid.UUID, user_id: uuid.UUID, *, bus: EventBus, open_session: SessionOpener
) -> AsyncIterator[str]:
    """This person's place in the queue, pushed until it stops being a place.

    Closes on the first snapshot that is not `waiting`: matched, expired or
    left. The client has the session id by then and goes to the room, so
    holding the connection open would be holding it for nothing.
    """

    async def snapshot() -> Snapshot:
        """This queue entry's current status, or close the stream if it is gone."""
        async with open_session() as session:
            try:
                status = await service.read_status(session, entry_id, user_id=user_id)
            except errors.QueueEntryNotFound:
                # Not this person's, or gone. Closing says so in the one way a
                # stream can; the client reads the route for the reason.
                raise StreamFinished from None
        return Snapshot(status.model_dump_json(), final=status.status != WAITING)

    return event_stream(topics=[user_topic(user_id)], snapshot=snapshot, bus=bus, owner=user_id)


# --- SSE for practice session phase and partner presence.

SESSION_TOPIC = "practice.session_updated"


def session_stream(
    session_id: uuid.UUID, user_id: uuid.UUID, *, bus: EventBus, open_session: SessionOpener
) -> AsyncIterator[str]:
    """Push session state until it ends."""

    async def snapshot() -> Snapshot:
        """This session's current read model, closing the stream once it ends."""
        from datetime import UTC, datetime

        async with open_session() as session:
            try:
                view = await service.read_session(session, session_id, user_id=user_id, now=datetime.now(UTC))
            except errors.SessionNotFound:
                raise StreamFinished from None
        payload = view.model_dump_json()
        final = view.status == "ended" or view.current_phase == "completed"
        return Snapshot(payload, final=final)

    topics = [user_topic(user_id), f"practice.session.{session_id}"]
    return event_stream(topics=topics, snapshot=snapshot, bus=bus, owner=user_id)
