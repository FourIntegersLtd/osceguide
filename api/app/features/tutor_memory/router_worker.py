"""The tool route the assistant worker calls.

The path is hardcoded in the worker (`livekit_assistant_worker/metadata.py`),
so it must be mounted at exactly this spelling. It lives in this slice rather
than in `assistant` because what a tool means is this slice's business;
`assistant` only says whose session it is and whether it is still running.
"""

from __future__ import annotations

import uuid
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_worker_secret
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.logging import get_logger
from app.core.ports import ClockDep
from app.features.tutor_memory import errors, schemas, service

router = APIRouter(tags=["worker"], dependencies=[Depends(require_worker_secret)])

log = get_logger(__name__)

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/assistant-sessions/{session_id}/tools/{tool_name}",
    response_model=schemas.ToolResult,
    responses=error_responses(
        Unauthenticated,
        errors.SessionNotFound,
        errors.SessionNotJoinable,
        errors.UnknownTool,
        errors.ToolArgumentsInvalid,
    ),
)
async def run_assistant_tool(
    session_id: uuid.UUID,
    tool_name: str,
    body: schemas.ToolCall,
    session: Session,
    clock: ClockDep,
) -> schemas.ToolResult:
    """One tool call. `result` is spoken; `display` goes to the browser unchanged.

    Timed, because this sits inside a voice loop. The model says a holding line
    and then waits on this round trip, so a slow tool is heard as a pause in
    the conversation rather than seen as a slow request — and nothing else in
    the system would show it. `search_material` is the one to watch: one
    embedding call plus one pgvector query, budgeted at about 350ms.
    """
    started = perf_counter()
    try:
        return await service.run_tool(
            session,
            session_id=session_id,
            tool=tool_name,
            arguments=body.arguments,
            now=clock.now(),
        )
    finally:
        log.info(
            "assistant tool call",
            tool=tool_name,
            session_id=str(session_id),
            ms=round((perf_counter() - started) * 1000),
        )
