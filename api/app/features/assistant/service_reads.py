"""Where a slice above `assistant` gets a word in.

`tutor_memory` knows what a dashboard session should be told, what its tools
mean and what becomes of its transcript. It sits above this slice and cannot be
imported from here, so `main.create_app` hands those three functions over and
this slice calls them without knowing whose they are.

Unbound, every one falls back to what this slice did before: placeholder
instructions, no tools, and the old "help sessions only" transcript rule. That
is what makes the seam safe to deploy ahead of the slice that fills it.

The reads below the seam are the other direction: what a slice above needs to
know about a session, as plain data rather than mapped rows.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.assistant import repository

RenderHook = Callable[[AsyncSession, str, uuid.UUID, datetime], Awaitable[dict[str, Any] | None]]
ToolHook = Callable[..., Awaitable[dict[str, Any]]]
TranscriptHook = Callable[[AsyncSession, uuid.UUID, str], Awaitable[bool]]

_render: RenderHook | None = None
_run_tool: ToolHook | None = None
_on_transcript: TranscriptHook | None = None


def bind_assistant_hooks(*, render: RenderHook, run_tool: ToolHook, on_transcript: TranscriptHook) -> None:
    """Tie the three places a slice above this one has something to say."""
    global _render, _run_tool, _on_transcript
    _render, _run_tool, _on_transcript = render, run_tool, on_transcript


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
