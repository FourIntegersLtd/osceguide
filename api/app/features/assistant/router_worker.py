"""Routes the LiveKit assistant worker calls.

Unlike the assessment worker, these paths are **hardcoded in the worker**
(`livekit_assistant_worker/metadata.py:9-12`) rather than configured per
backend, so this API must mount them at exactly these spellings. Worth changing
in the worker eventually; until then, moving them here breaks it.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_worker_secret
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.ports import ClockDep
from app.features.assistant import errors, schemas, service_worker

router = APIRouter(tags=["worker"], dependencies=[Depends(require_worker_secret)])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/assistant-sessions/{session_id}",
    response_model=schemas.WorkerSessionPayload,
    responses=error_responses(Unauthenticated, errors.SessionNotFound, errors.SessionNotJoinable),
)
async def bootstrap_assistant_session(
    session_id: uuid.UUID, session: Session
) -> schemas.WorkerSessionPayload:
    return await service_worker.bootstrap(session, session_id)


@router.post(
    "/assistant-sessions/{session_id}/scene",
    response_model=schemas.SceneInstructions,
    responses=error_responses(Unauthenticated, errors.SessionNotFound),
)
async def assistant_scene(
    session_id: uuid.UUID, body: schemas.SceneRequest, session: Session
) -> schemas.SceneInstructions:
    return schemas.SceneInstructions(
        instructions=await service_worker.scene_instructions(session, session_id, phase=body.phase)
    )


@router.post(
    "/assistant-sessions/{session_id}/transcript",
    response_model=schemas.Accepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Unauthenticated, errors.SessionNotFound),
)
async def accept_assistant_transcript(
    session_id: uuid.UUID,
    body: schemas.AssistantTranscriptPost,
    session: Session,
    clock: ClockDep,
) -> schemas.Accepted:
    await service_worker.accept_transcript(session, session_id, transcript=body.transcript, now=clock.now())
    return schemas.Accepted()


@router.post(
    "/sessions/{session_id}/complete",
    response_model=schemas.Accepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Unauthenticated, errors.SessionNotFound),
)
async def complete_assistant_session(
    session_id: uuid.UUID,
    body: schemas.SessionComplete,
    session: Session,
    clock: ClockDep,
) -> schemas.Accepted:
    """The GPT-Live path reports usage and why the session ended."""
    await service_worker.complete_session(
        session,
        session_id,
        end_reason=body.end_reason,
        usage=body.usage,
        now=clock.now(),
    )
    return schemas.Accepted()
