"""Routes the LiveKit assessment worker calls.

Mounted under `/api/worker`, every one guarded by the shared secret, which
fails closed: `core.settings` refuses to start in staging or production without
it. Both legacy backends' guards returned early when the variable was unset,
which quietly exposed the patient persona and — for a debrief — the candidate's
prior transcript and feedback.
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
from app.features.attempts import errors, schemas
from app.features.attempts import service_worker as service

router = APIRouter(
    tags=["worker"],
    dependencies=[Depends(require_worker_secret)],
)

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/attempts/{attempt_id}",
    response_model=schemas.WorkerBootstrap,
    responses=error_responses(
        Unauthenticated,
        errors.AttemptNotFound,
        errors.AttemptNotReady,
        errors.StationNotPublishedError,
    ),
)
async def bootstrap(attempt_id: uuid.UUID, session: Session, clock: ClockDep) -> schemas.WorkerBootstrap:
    return await service.bootstrap(session, attempt_id, now=clock.now())


# Store one turn as it is spoken. Posted best-effort, so duplicates are expected and ignored.
@router.post(
    "/attempts/{attempt_id}/transcript-chunks",
    response_model=schemas.WorkerAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Unauthenticated, errors.AttemptNotFound, errors.AttemptMismatch),
)
async def accept_chunk(
    attempt_id: uuid.UUID, body: schemas.ChunkPost, session: Session
) -> schemas.WorkerAccepted:
    await service.accept_chunk(session, attempt_id, body_attempt_id=body.attempt_id, message=body.message)
    return schemas.WorkerAccepted()


# Mark the delivery complete and queue marking, once the whole transcript has arrived.
@router.post(
    "/attempts/{attempt_id}/transcript",
    response_model=schemas.WorkerAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Unauthenticated, errors.AttemptNotFound, errors.AttemptMismatch),
)
async def accept_transcript(
    attempt_id: uuid.UUID, body: schemas.TranscriptPost, session: Session, clock: ClockDep
) -> schemas.WorkerAccepted:
    await service.accept_transcript(
        session,
        attempt_id,
        body_attempt_id=body.attempt_id,
        transcript=body.transcript,
        now=clock.now(),
    )
    return schemas.WorkerAccepted()
