from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.features.station_sets import errors, schemas, service

router = APIRouter(tags=["station-sets"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/me/station-sets",
    response_model=Page[schemas.SetRead],
    responses=error_responses(Unauthenticated),
)
async def list_sets(
    principal: CurrentPrincipal, session: Session, page: Annotated[CursorParams, Depends()]
) -> Page[schemas.SetRead]:
    """Each set carries its own progress, so the list does not need a call per
    station to work out how far along someone is."""
    items, next_cursor = await service.list_sets(
        session, principal.user_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=items, next_cursor=next_cursor)


@router.post(
    "/me/station-sets",
    response_model=schemas.SetRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Unauthenticated),
)
async def create_set(
    body: schemas.CreateSet, principal: CurrentPrincipal, session: Session
) -> schemas.SetRead:
    return await service.create_set(
        session,
        principal.user_id,
        name=body.name,
        exam_code=body.exam_code,
        station_version_ids=body.station_version_ids,
    )


@router.get(
    "/me/station-sets/{set_id}",
    response_model=schemas.SetRead,
    responses=error_responses(Unauthenticated, errors.SetNotFound),
)
async def read_set(set_id: uuid.UUID, principal: CurrentPrincipal, session: Session) -> schemas.SetRead:
    return await service.read_set(session, principal.user_id, set_id)


@router.post(
    "/me/station-sets/{set_id}/entries/{entry_id}/attempts",
    response_model=schemas.StartedAttempt,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        Unauthenticated,
        errors.NotEntitled,
        errors.SetNotFound,
        errors.EntryNotFound,
        errors.AttemptLimitReachedError,
        errors.SetLockedError,
    ),
)
async def start_attempt(
    set_id: uuid.UUID,
    entry_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: Session,
    clock: ClockDep,
) -> schemas.StartedAttempt:
    return await service.start_entry_attempt(session, principal.user_id, set_id, entry_id, now=clock.now())
