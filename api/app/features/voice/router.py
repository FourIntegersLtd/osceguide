from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.ports import VoiceTokens
from app.core.settings import SettingsDep
from app.features.voice import errors, schemas, service

router = APIRouter(tags=["voice"])

Session = Annotated[AsyncSession, Depends(get_session)]


# Issue a LiveKit token for the room this attempt's live station runs in.
@router.post(
    "/attempts/{attempt_id}/voice-token",
    response_model=schemas.VoiceGrant,
    responses=error_responses(
        Unauthenticated,
        errors.AttemptNotFound,
        errors.AttemptNotYours,
        errors.AttemptNotJoinable,
        errors.VoiceUnavailable,
    ),
)
async def issue_voice_token(
    attempt_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: Session,
    settings: SettingsDep,
    tokens: Annotated[VoiceTokens, Depends(service.get_voice_tokens)],
) -> schemas.VoiceGrant:
    return await service.grant_for_attempt(
        session,
        attempt_id,
        requester_id=principal.user_id,
        tokens=tokens,
        settings=settings,
    )
