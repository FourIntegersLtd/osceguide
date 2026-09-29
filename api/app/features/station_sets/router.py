"""HTTP routes for a learner's own practice sets: build one, run or debrief its stations."""

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
    responses=error_responses(errors.UnknownExamError, errors.NotEntitled, Unauthenticated),
)
async def list_sets(
    principal: CurrentPrincipal, session: Session, page: Annotated[CursorParams, Depends()]
) -> Page[schemas.SetRead]:
    """Each set carries its own progress, so the list does not need a call per
    station to work out how far along someone is."""
    sets, next_cursor = await service.list_sets(
        session, principal.user_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=sets, next_cursor=next_cursor)


# Builds the set and all its entries from the given stations in one call.
@router.post(
    "/me/station-sets",
    response_model=schemas.SetRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(errors.UnknownExamError, errors.NotEntitled, Unauthenticated),
)
async def create_set(
    body: schemas.CreateSet, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.SetRead:
    return await service.create_set(
        session,
        principal.user_id,
        name=body.name,
        exam_code=body.exam_code,
        station_version_ids=body.station_version_ids,
        now=clock.now(),
    )


@router.get(
    "/me/station-sets/{set_id}",
    response_model=schemas.SetRead,
    responses=error_responses(Unauthenticated, errors.SetNotFound),
)
async def read_set(set_id: uuid.UUID, principal: CurrentPrincipal, session: Session) -> schemas.SetRead:
    return await service.read_set(session, principal.user_id, set_id)


@router.patch(
    "/me/station-sets/{set_id}",
    response_model=schemas.SetRead,
    responses=error_responses(
        Unauthenticated,
        errors.SetNotFound,
        errors.SetLockedError,
        errors.StationVersionNotUsableError,
        errors.EntryHasAttemptsError,
    ),
)
async def update_set(
    set_id: uuid.UUID, body: schemas.UpdateSet, principal: CurrentPrincipal, session: Session
) -> schemas.SetRead:
    """Rename one of your own practice sets, and — the legacy "edit session" screen — swap its stations.

    Owner-only, and a set that is not yours answers 404 rather than 403: an id
    is not something a stranger should be able to confirm exists by the shape
    of the refusal. `station_version_ids` left out of the body changes only the
    name; given, it replaces the set's stations first (which can itself refuse:
    the set is locked, a version cannot be used, or an entry being dropped has
    already been attempted) and renames the result.
    """
    if body.station_version_ids is not None:
        await service.replace_entries(
            session, principal.user_id, set_id, station_version_ids=body.station_version_ids
        )
    return await service.rename_set(session, principal.user_id, set_id, name=body.name)


@router.delete(
    "/me/station-sets/{set_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Unauthenticated, errors.SetNotFound, errors.SetHasAttemptsError),
)
async def delete_set(set_id: uuid.UUID, principal: CurrentPrincipal, session: Session) -> None:
    """Throw a practice set away.

    Refused if the set holds any attempts, so a station somebody has already sat is never left
    pointing at a deleted set. Use the platform console's progress-deletion route to remove a set's
    attempts first.
    """
    await service.delete_set(session, principal.user_id, set_id)


# Flag a station in your own set to come back to, or take the flag off.
@router.put(
    "/me/station-sets/{set_id}/entries/{entry_id}/flag",
    response_model=schemas.SetRead,
    responses=error_responses(Unauthenticated, errors.SetNotFound, errors.EntryNotFound),
)
async def flag_set_entry(
    set_id: uuid.UUID,
    entry_id: uuid.UUID,
    body: schemas.FlagEntry,
    principal: CurrentPrincipal,
    session: Session,
    clock: ClockDep,
) -> schemas.SetRead:
    return await service.flag_entry(
        session, principal.user_id, set_id, entry_id, flagged=body.flagged, now=clock.now()
    )


# Every station you have flagged across your sets, most recently flagged first.
@router.get(
    "/me/flagged-stations",
    response_model=list[schemas.FlaggedEntryRead],
    responses=error_responses(Unauthenticated),
)
async def list_flagged_stations(
    principal: CurrentPrincipal, session: Session
) -> list[schemas.FlaggedEntryRead]:
    return await service.list_flagged(session, principal.user_id)


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


@router.post(
    "/me/station-sets/{set_id}/entries/{entry_id}/debriefs",
    response_model=schemas.StartedAttempt,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        Unauthenticated,
        errors.NotEntitled,
        errors.SetNotFound,
        errors.EntryNotFound,
        errors.AttemptLimitReachedError,
        errors.NothingToDebriefError,
    ),
)
async def start_debrief(
    set_id: uuid.UUID,
    entry_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: Session,
    clock: ClockDep,
) -> schemas.StartedAttempt:
    """Talk through an attempt you have already made.

    Its own route rather than a flag on the one above, because it is a
    different act with a different limit and a different refusal: a debrief is
    *about* an earlier attempt, and `nothing_to_debrief` is what you get for
    asking to discuss a station you have not sat.

    `start_entry_attempt(debrief=True)` has been written and tested since the
    slice landed, and nothing called it — the b2c debrief had no way in.
    """
    return await service.start_entry_attempt(
        session, principal.user_id, set_id, entry_id, now=clock.now(), debrief=True
    )
