"""SSE for practice session phase and partner presence."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from app.core.db import SessionOpener
from app.core.events import user_topic
from app.core.ports import EventBus
from app.core.sse import Snapshot, StreamFinished, event_stream
from app.features.peer_practice import errors, service

SESSION_TOPIC = "practice.session_updated"


def session_stream(
    session_id: uuid.UUID, user_id: uuid.UUID, *, bus: EventBus, open_session: SessionOpener
) -> AsyncIterator[str]:
    """Push session state until it ends."""

    async def snapshot() -> Snapshot:
        from datetime import UTC, datetime

        async with open_session() as session:
            try:
                view = await service.read_session(
                    session, session_id, user_id=user_id, now=datetime.now(UTC)
                )
            except errors.SessionNotFound:
                raise StreamFinished from None
        payload = view.model_dump_json()
        final = view.status == "ended" or view.current_phase == "completed"
        return Snapshot(payload, final=final)

    topics = [user_topic(user_id), f"practice.session.{session_id}"]
    return event_stream(topics=topics, snapshot=snapshot, bus=bus)
