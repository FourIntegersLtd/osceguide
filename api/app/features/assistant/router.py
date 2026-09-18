from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.ports import VoiceTokens
from app.core.settings import SettingsDep
from app.features.assistant import errors, schemas, service

router = APIRouter(tags=["assistant"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/assistant/sessions",
    response_model=schemas.SessionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Unauthenticated, errors.UnknownAssistantTypeError),
)
async def start_session(
    body: schemas.StartSession, principal: CurrentPrincipal, session: Session
) -> schemas.SessionRead:
    return await service.start_session(
        session,
        user_id=principal.user_id,
        session_type=body.session_type,
        extras=body.extras,
    )


@router.post(
    "/assistant/sessions/{session_id}/voice-token",
    response_model=schemas.RoomGrant,
    responses=error_responses(
        Unauthenticated,
        errors.SessionNotFound,
        errors.SessionNotYours,
        errors.SessionNotJoinable,
        errors.VoiceUnavailable,
    ),
)
async def issue_session_voice_token(
    session_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: Session,
    settings: SettingsDep,
    tokens: Annotated[VoiceTokens, Depends(service.get_voice_tokens)],
) -> schemas.RoomGrant:
    """The browser's way into an assistant session's room."""
    return await service.voice_grant(
        session,
        session_id,
        requester_id=principal.user_id,
        tokens=tokens,
        settings=settings,
    )
