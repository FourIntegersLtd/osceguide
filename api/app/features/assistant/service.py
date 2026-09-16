"""Assistant session use cases, including the worker's side."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.assistant import domain, errors, repository
from app.features.assistant.models import AssistantSession
from app.features.assistant.schemas import SessionRead, WorkerSessionPayload

# Placeholder text until content packs are ported. Rendered here rather than in
# the worker, which holds no templates by design.
_INSTRUCTIONS = {
    "help": "You are helping someone use OSCE Guide. Answer from the FAQ you have been given.",
    "onboarding": "You are introducing OSCE Guide to someone using it for the first time.",
    "dashboard": "You are talking someone through their progress.",
    "consulting-doctor": "You are a doctor demonstrating a consultation.",
}


async def start_session(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    session_type: str,
    extras: dict[str, Any],
) -> SessionRead:
    try:
        worker_type = domain.worker_type_for(session_type)
    except domain.UnknownAssistantType as exc:
        raise errors.UnknownAssistantTypeError(str(exc)) from exc

    instructions = _INSTRUCTIONS[worker_type]
    try:
        domain.ensure_dispatchable(instructions=instructions)
    except domain.UnrenderableSession as exc:
        raise errors.SessionNotReady(str(exc)) from exc

    row = await repository.create_session(
        session,
        user_id=user_id,
        session_type=worker_type,
        instructions=instructions,
        greeting=None,
        extras=extras,
        room_name=None,
    )
    # The room is derived from the session id, so a stray room says which
    # session it belongs to.
    await repository.set_room(session, row.id, room_name=f"assistant_{row.id}")
    refreshed = await repository.by_id(session, row.id)
    return _read(refreshed)  # type: ignore[arg-type]


async def bootstrap(session: AsyncSession, session_id: uuid.UUID) -> WorkerSessionPayload:
    """What the assistant worker fetches.

    Mirrors `livekit_assistant_worker.bootstrap.AssistantSession`: every text
    arrives rendered, and `extras` carries the two facts the worker decides for
    itself.
    """
    row = await _require(session, session_id)
    if not domain.can_join(status=row.status):
        raise errors.SessionNotJoinable()
    try:
        domain.ensure_dispatchable(instructions=row.instructions)
    except domain.UnrenderableSession as exc:
        raise errors.SessionNotReady(str(exc)) from exc

    return WorkerSessionPayload(
        session={
            "session_id": str(row.id),
            "worker_type": row.session_type,
            "candidate_ref": str(row.user_id),
            "instructions": row.instructions,
            "greeting": row.greeting,
            "extras": row.extras or {},
        }
    )


async def scene_instructions(session: AsyncSession, session_id: uuid.UUID, *, phase: str | None) -> str:
    """Instructions for the next scene of an onboarding demo."""
    row = await _require(session, session_id)
    return f"{row.instructions}\n\nScene: {phase or 'next'}."


async def accept_transcript(
    session: AsyncSession, session_id: uuid.UUID, *, transcript: dict[str, Any], now: datetime
) -> None:
    """Store a help session's turns; discard everyone else's.

    The other three kinds are navigation, and keeping them would collect
    recordings of people's screens for no purpose.
    """
    row = await _require(session, session_id)
    if not domain.keeps_transcript(row.session_type):
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
    await _require(session, session_id)
    await repository.complete(session, session_id, at=now, end_reason=end_reason, usage=usage or None)


async def _require(session: AsyncSession, session_id: uuid.UUID) -> AssistantSession:
    row = await repository.by_id(session, session_id)
    if row is None:
        raise errors.SessionNotFound()
    return row


def _read(row: AssistantSession) -> SessionRead:
    return SessionRead(
        id=row.id,
        session_type=row.session_type,
        status=row.status,
        room_name=row.room_name,
        created_at=row.created_at,
    )
