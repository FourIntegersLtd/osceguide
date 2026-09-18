from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.pagination import Page
from app.core.ports import ClockDep
from app.features.attempts import errors, schemas, service, service_reads

router = APIRouter(tags=["attempts"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/attempts",
    response_model=schemas.AttemptRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        Unauthenticated,
        errors.NotEntitled,
        errors.UnknownExamError,
        errors.StationNotFound,
        errors.StationNotPublishedError,
    ),
)
async def start_attempt(
    body: schemas.CreateAttempt,
    principal: CurrentPrincipal,
    session: Session,
    clock: ClockDep,
) -> schemas.AttemptRead:
    active = principal.active_membership
    return await service.start_attempt(
        session,
        user_id=principal.user_id,
        kind=body.kind,
        exam_code=body.exam_code,
        now=clock.now(),
        org_id=active.org_id if active else None,
        station_version_id=body.station_version_id,
    )


@router.post(
    "/attempts/{attempt_id}/abandon",
    response_model=schemas.AttemptRead,
    responses=error_responses(
        Unauthenticated,
        errors.AttemptNotFound,
        errors.AttemptNotYours,
        errors.InvalidAttemptState,
    ),
)
async def abandon_attempt(
    attempt_id: uuid.UUID, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.AttemptRead:
    """The candidate walks away before finishing.

    Otherwise the attempt stays `running` forever, holding the slot's one live
    attempt and counting as in progress on every screen that reads it.
    """
    return await service.abandon_attempt(
        session,
        attempt_id,
        requester_id=principal.user_id,
        is_admin=principal.is_platform_admin,
        now=clock.now(),
    )


@router.get(
    "/attempts/{attempt_id}",
    response_model=schemas.AttemptRead,
    responses=error_responses(Unauthenticated, errors.AttemptNotFound, errors.AttemptNotYours),
)
async def read_attempt(
    attempt_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> schemas.AttemptRead:
    return await service_reads.read_attempt(
        session,
        attempt_id,
        requester_id=principal.user_id,
        is_admin=principal.is_platform_admin,
    )


@router.get(
    "/attempts/{attempt_id}/transcript",
    response_model=schemas.TranscriptRead,
    responses=error_responses(Unauthenticated, errors.AttemptNotFound, errors.AttemptNotYours),
)
async def read_transcript(
    attempt_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> schemas.TranscriptRead:
    return await service_reads.read_transcript(
        session,
        attempt_id,
        requester_id=principal.user_id,
        is_admin=principal.is_platform_admin,
    )


@router.get(
    "/attempts/{attempt_id}/result",
    response_model=Page[schemas.AssessmentResultRead],
    responses=error_responses(Unauthenticated, errors.AttemptNotFound, errors.AttemptNotYours),
)
async def read_results(
    attempt_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> Page[schemas.AssessmentResultRead]:
    """A page rather than one result: re-scoring under a new policy adds beside
    the old, so a candidate's history stays readable."""
    items = await service_reads.read_results(
        session,
        attempt_id,
        requester_id=principal.user_id,
        is_admin=principal.is_platform_admin,
    )
    return Page(items=items, next_cursor=None)
