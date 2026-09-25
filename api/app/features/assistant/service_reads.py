"""What another slice may read about an assistant session, as plain data rather than mapped rows."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.assistant import repository


@dataclass(frozen=True)
class SessionRef:
    """An assistant session, as another slice may see one."""

    id: uuid.UUID
    user_id: uuid.UUID
    session_type: str
    status: str


async def session_ref(session: AsyncSession, session_id: uuid.UUID) -> SessionRef | None:
    row = await repository.by_id(session, session_id)
    if row is None:
        return None
    return SessionRef(id=row.id, user_id=row.user_id, session_type=row.session_type, status=row.status)


async def transcript_messages(session: AsyncSession, session_id: uuid.UUID) -> list[dict[str, Any]]:
    """This session's turns, in order, as plain dicts.

    Dicts rather than rows: a mapped class handed to another slice can drag a
    lazy relationship along with it, which is why a guard forbids it.
    """
    return [
        {"role": row.role, "message": row.message, "seq": row.seq}
        for row in await repository.messages_for(session, session_id)
    ]


async def discard_transcript(session: AsyncSession, session_id: uuid.UUID) -> int:
    """Delete a session's turns once something durable has replaced them.

    Called by whoever wrote that replacement, never speculatively: the turns
    are the only record until the summary exists.
    """
    return await repository.delete_messages(session, session_id)
