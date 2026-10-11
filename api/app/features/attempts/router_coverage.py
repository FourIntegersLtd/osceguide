"""HTTP route for the live coverage panel shown while a station is still running."""

import uuid

from fastapi import APIRouter

from app.core.auth import CurrentPrincipal
from app.core.db import SessionDep
from app.core.errors import Unauthenticated, error_responses
from app.features.attempts import errors, service_coverage
from app.features.attempts.schemas import CoverageRead

router = APIRouter()


# Read which marking points a consultation covered, for the person who sat it.
@router.get(
    "/attempts/{attempt_id}/coverage",
    response_model=CoverageRead,
    responses=error_responses(Unauthenticated, errors.AttemptNotFound, errors.AttemptNotYours),
)
async def read_coverage(
    attempt_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: SessionDep,
) -> CoverageRead:
    return await service_coverage.read_coverage(session, attempt_id, requester_id=principal.user_id)
