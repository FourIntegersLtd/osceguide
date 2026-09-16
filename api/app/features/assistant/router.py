from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
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
