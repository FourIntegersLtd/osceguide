"""Browser-facing assistant routes: start a session, join its room, read onboarding scenes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.ports import ClockDep, VoiceTokens
from app.core.rate_limit import AI_SPEND, TooManyRequests, per_user
from app.core.settings import SettingsDep
from app.features.assistant import errors, schemas, service, service_content

router = APIRouter(tags=["assistant"])

Session = Annotated[AsyncSession, Depends(get_session)]


# Start an assistant session of the given type, rendered for the caller.
@router.post(
    "/assistant/sessions",
    response_model=schemas.SessionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(TooManyRequests, Unauthenticated, errors.UnknownAssistantTypeError),
    dependencies=[Depends(per_user(AI_SPEND))],
)
async def start_session(
    body: schemas.StartSession, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.SessionRead:
    membership = principal.active_membership
    return await service.start_session(
        session,
        user_id=principal.user_id,
        # Scopes the station lookup (SEC-007) to what the caller may see: their
        # org's stations, or the platform library for a consumer with no org.
        org_id=membership.org_id if membership else None,
        session_type=body.session_type,
        extras=body.extras,
        station_version_id=body.station_version_id,
        now=clock.now(),
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


@router.get(
    "/assistant/onboarding-scenes",
    response_model=schemas.OnboardingScenes,
    responses=error_responses(Unauthenticated),
)
async def read_onboarding_scenes(principal: CurrentPrincipal, session: Session) -> schemas.OnboardingScenes:
    """The demo scenarios a first-time user is walked through.

    Answered from the same pack the onboarding session's instructions are
    rendered from, and for the caller's own exam — a headache for SCA, chest
    pain for PLAB — so the introduction is to the thing they are sitting.
    """
    pack = await service_content.pack_for(session, user_id=principal.user_id, extras={})
    return schemas.OnboardingScenes(
        scenes=[
            schemas.OnboardingScene(patientLine=scene.patient_line, question=scene.question)
            for scene in pack.onboarding_scenes
        ],
        persona=schemas.AssistantPersona(assistantName=pack.persona.assistant_name),
    )
