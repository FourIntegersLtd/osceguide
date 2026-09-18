"""The worker side of the assistant contract.

Split from `service.py` so the browser-facing use cases and the machine-facing
ones can be read on their own; they change for different reasons, and together
they were past the file cap.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.assistant import domain, errors, repository
from app.features.assistant import service_seams as seams
from app.features.assistant.schemas import WorkerSessionPayload
from app.features.assistant.service import TOOLS_KEY, require_session


async def bootstrap(session: AsyncSession, session_id: uuid.UUID) -> WorkerSessionPayload:
    """What the assistant worker fetches.

    Mirrors `livekit_assistant_worker.bootstrap.AssistantSession`: every text
    arrives rendered, and `extras` carries the two facts the worker decides for
    itself.
    """
    row = await require_session(session, session_id)
    if not domain.can_join(status=row.status):
        raise errors.SessionNotJoinable()
    try:
        domain.ensure_dispatchable(instructions=row.instructions)
    except domain.UnrenderableSession as exc:
        raise errors.SessionNotReady(str(exc)) from exc

    stored = dict(row.extras or {})
    tools = stored.pop(TOOLS_KEY, [])
    return WorkerSessionPayload(
        session={
            "session_id": str(row.id),
            "worker_type": row.session_type,
            "candidate_ref": str(row.user_id),
            "instructions": row.instructions,
            "greeting": row.greeting,
            "extras": stored,
            # `livekit_assistant_worker.bootstrap.AssistantSession.tools`. An
            # empty list is the whole of the old behaviour, which is why the
            # worker change could ship before any backend defined a tool.
            "tools": tools,
        }
    )


async def scene_instructions(session: AsyncSession, session_id: uuid.UUID, *, phase: str | None) -> str:
    """Instructions for the next scene of an onboarding demo."""
    row = await require_session(session, session_id)
    return f"{row.instructions}\n\nScene: {phase or 'next'}."


async def accept_transcript(
    session: AsyncSession, session_id: uuid.UUID, *, transcript: dict[str, Any], now: datetime
) -> None:
    """Store a help session's turns; discard everyone else's.

    The other three kinds are navigation, and keeping them would collect
    recordings of people's screens for no purpose.
    """
    row = await require_session(session, session_id)
    # Whether to keep this kind of conversation is decided above this slice
    # once `tutor_memory` is bound: a dashboard session is summarised and then
    # deleted, which is neither "keep" nor "discard". Unbound, this is the old
    # rule exactly.
    keep = (
        await seams._on_transcript(session, session_id, row.session_type)
        if seams._on_transcript
        else domain.keeps_transcript(row.session_type)
    )
    if not keep:
        return

    seen = await repository.seen_message_ids(session, session_id)
    for message in transcript.get("messages") or []:
        message_id = str(message.get("message_id") or "")
        if not message_id or message_id in seen:
            continue
        seen.add(message_id)
        await repository.add_message(
            session,
            session_id,
            message_id=message_id,
            seq=int(message.get("seq") or 0),
            role=str(message.get("role") or "user"),
            message=str(message.get("message") or ""),
            spoken_at=now,
        )


async def complete_session(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    end_reason: str | None,
    usage: dict[str, Any],
    now: datetime,
) -> None:
    await require_session(session, session_id)
    await repository.complete(session, session_id, at=now, end_reason=end_reason, usage=usage or None)
