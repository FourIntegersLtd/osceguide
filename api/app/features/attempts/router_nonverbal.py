"""HTTP routes for non-verbal feedback: the candidate's read, the camera batches, and consent."""

import uuid

from fastapi import APIRouter, status

from app.core.auth import CurrentPrincipal
from app.core.db import SessionDep
from app.core.errors import Unauthenticated, error_responses
from app.core.ports import ClockDep
from app.features.attempts import errors, schemas_nonverbal, service_nonverbal
from app.features.attempts.schemas import WorkerAccepted

router = APIRouter()


# Read the candidate's own non-verbal feedback state for one attempt.
@router.get(
    "/attempts/{attempt_id}/nonverbal",
    response_model=schemas_nonverbal.NonverbalRead,
    responses=error_responses(Unauthenticated, errors.AttemptNotFound, errors.AttemptNotYours),
)
async def read_nonverbal(
    attempt_id: uuid.UUID, principal: CurrentPrincipal, session: SessionDep
) -> schemas_nonverbal.NonverbalRead:
    return await service_nonverbal.read(session, attempt_id, requester_id=principal.user_id)


# Accept one batch of per-second camera measurements. Late batches are accepted and dropped.
@router.post(
    "/attempts/{attempt_id}/nonverbal-batches",
    response_model=WorkerAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(
        Unauthenticated,
        errors.AttemptNotFound,
        errors.AttemptNotYours,
        errors.NonverbalNotAvailable,
        errors.NonverbalConsentRequired,
    ),
)
async def post_nonverbal_batch(
    attempt_id: uuid.UUID,
    body: schemas_nonverbal.NonverbalBatchIn,
    principal: CurrentPrincipal,
    session: SessionDep,
    clock: ClockDep,
) -> WorkerAccepted:
    await service_nonverbal.accept_batch(
        session, attempt_id, requester_id=principal.user_id, batch=body, now=clock.now()
    )
    return WorkerAccepted()


# Turn non-verbal feedback on or off for the signed-in person; turning it off deletes their stored data.
@router.put(
    "/me/nonverbal-consent",
    response_model=schemas_nonverbal.NonverbalRead,
    responses=error_responses(Unauthenticated, errors.NonverbalConsentVersionStale),
)
async def put_nonverbal_consent(
    body: schemas_nonverbal.NonverbalConsentIn,
    principal: CurrentPrincipal,
    session: SessionDep,
    clock: ClockDep,
) -> schemas_nonverbal.NonverbalRead:
    return await service_nonverbal.set_consent(
        session, principal.user_id, consented=body.consented, version=body.version, now=clock.now()
    )
