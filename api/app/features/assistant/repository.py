"""Storage for assistant sessions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.assistant.models import AssistantSession, AssistantTranscriptMessage


async def create_session(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    session_type: str,
    instructions: str,
    greeting: str | None,
    extras: dict[str, Any] | None,
    room_name: str | None,
) -> AssistantSession:
    row = AssistantSession(
        user_id=user_id,
        session_type=session_type,
        instructions=instructions,
        greeting=greeting,
        extras=extras,
        room_name=room_name,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def set_room(session: AsyncSession, session_id: uuid.UUID, *, room_name: str) -> None:
    await session.execute(
        update(AssistantSession).where(AssistantSession.id == session_id).values(room_name=room_name)
    )


async def by_id(session: AsyncSession, session_id: uuid.UUID) -> AssistantSession | None:
    stmt = select(AssistantSession).where(AssistantSession.id == session_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def complete(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    at: datetime,
    end_reason: str | None,
    usage: dict[str, Any] | None,
) -> None:
    await session.execute(
        update(AssistantSession)
        .where(AssistantSession.id == session_id)
        .values(status="completed", completed_at=at, end_reason=end_reason, usage=usage)
    )


async def seen_message_ids(session: AsyncSession, session_id: uuid.UUID) -> set[str]:
    stmt = select(AssistantTranscriptMessage.message_id).where(
        AssistantTranscriptMessage.session_id == session_id
    )
    return set((await session.execute(stmt)).scalars())


async def add_message(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    message_id: str,
    seq: int,
    role: str,
    message: str,
    spoken_at: datetime,
) -> None:
    session.add(
        AssistantTranscriptMessage(
            session_id=session_id,
            message_id=message_id,
            seq=seq,
            role=role,
            message=message,
            spoken_at=spoken_at,
        )
    )
    await session.flush()


async def messages_for(session: AsyncSession, session_id: uuid.UUID) -> list[AssistantTranscriptMessage]:
    stmt = (
        select(AssistantTranscriptMessage)
        .where(AssistantTranscriptMessage.session_id == session_id)
        .order_by(AssistantTranscriptMessage.seq)
    )
    return list((await session.execute(stmt)).scalars())
