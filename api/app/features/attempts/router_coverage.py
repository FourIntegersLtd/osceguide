import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.features.attempts import errors, service_coverage
from app.features.attempts.schemas import CoverageRead

router = APIRouter()


@router.get(
    "/attempts/{attempt_id}/coverage",
    response_model=CoverageRead,
    responses=error_responses(Unauthenticated, errors.AttemptNotFound, errors.AttemptNotYours),
)
async def read_coverage(
    attempt_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CoverageRead:
    return await service_coverage.read_coverage(session, attempt_id, requester_id=principal.user_id)
