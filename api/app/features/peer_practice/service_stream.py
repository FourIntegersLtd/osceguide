"""Telling somebody in the queue that they have been matched.

The status route says in its own docstring that the client polls it every few
seconds, which is the worst place in the product to poll: the person is sitting
and staring at the screen, and the whole feature is how quickly they get into a
room with somebody.

The matcher is a periodic job, not a request, so this is also the proof that
the event path works from `job_session` — it flushes what the job queued once
the pairing has committed, exactly as a request does.
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
        async with open_session() as session:
            try:
                status = await service.read_status(session, entry_id, user_id=user_id)
            except errors.QueueEntryNotFound:
                # Not this person's, or gone. Closing says so in the one way a
                # stream can; the client reads the route for the reason.
                raise StreamFinished from None
        return Snapshot(status.model_dump_json(), final=status.status != WAITING)

    return event_stream(topics=[user_topic(user_id)], snapshot=snapshot, bus=bus)
