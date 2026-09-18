"""The tool route the assistant worker calls.

The path is hardcoded in the worker (`livekit_assistant_worker/metadata.py`),
so it must be mounted at exactly this spelling. It lives in this slice rather
than in `assistant` because what a tool means is this slice's business;
`assistant` only says whose session it is and whether it is still running.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_worker_secret
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.ports import ClockDep
from app.features.tutor_memory import errors, schemas, service

router = APIRouter(tags=["worker"], dependencies=[Depends(require_worker_secret)])

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
    """One tool call. `result` is spoken; `display` goes to the browser unchanged."""
    return await service.run_tool(
        session,
        session_id=session_id,
        tool=tool_name,
        arguments=body.arguments,
        now=clock.now(),
    )
