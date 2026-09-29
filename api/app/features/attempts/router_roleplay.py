"""Post-consultation practice from either side of the encounter."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.ports import ClockDep
from app.core.rate_limit import AI_SPEND, TooManyRequests, per_user
from app.features.attempts import errors, schemas, service_debrief, service_material
from app.features.attempts.schemas import PatientRoleplayRead

router = APIRouter()
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/attempts/{attempt_id}/roleplay",
    response_model=PatientRoleplayRead,
    responses=error_responses(
        Unauthenticated,
        errors.AttemptNotFound,
        errors.AttemptNotYours,
        errors.AttemptNotReady,
        errors.AttemptNotFinished,
    ),
)
async def read_roleplay(
    attempt_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> PatientRoleplayRead:
    return await service_material.read_roleplay(session, attempt_id, requester_id=principal.user_id)


# Start a standalone debrief conversation about a finished consultation.
@router.post(
    "/attempts/{attempt_id}/debriefs",
    response_model=schemas.AttemptRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        TooManyRequests,
        Unauthenticated,
        errors.AttemptNotFound,
        errors.AttemptNotYours,
        errors.AttemptNotReady,
        errors.AttemptNotFinished,
    ),
    dependencies=[Depends(per_user(AI_SPEND))],
)
async def start_debrief(
    attempt_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: Session,
    clock: ClockDep,
) -> schemas.AttemptRead:
    return await service_debrief.start_debrief_attempt(
        session,
        user_id=principal.user_id,
        source_attempt_id=attempt_id,
        now=clock.now(),
        standalone=True,
    )
