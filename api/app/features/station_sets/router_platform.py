"""The platform console's view of one person's station progress. Every route
is `PlatformAdmin`.

The two writes are the retiring B2C admin's "reset attempts" and "delete
station", carried across with the same meaning. Both are audited.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.tenancy import PlatformAdmin
from app.features.station_sets import errors, schemas, service_platform

router = APIRouter(tags=["station-sets"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/platform/users/{user_id}/stations",
    response_model=list[schemas.StationProgressRead],
    responses=error_responses(Forbidden, errors.UserNotFound),
)
async def list_station_progress_for_support(
    user_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> list[schemas.StationProgressRead]:
    """One row per station this person has sat: attempts, how many were
    marked, the newest one, and the counters their practice sets hold."""
    _ = admin
    return await service_platform.station_progress(session, user_id)


@router.post(
    "/platform/users/{user_id}/stations/{station_id}/reset-attempts",
    response_model=schemas.StationProgressChange,
    responses=error_responses(Forbidden, errors.UserNotFound, errors.StationNotFound),
)
async def reset_station_attempts_for_support(
    user_id: uuid.UUID, station_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.StationProgressChange:
    """Set the person's attempt counters for this station back to zero. The
    attempts and their marking are kept."""
    return await service_platform.reset_attempts(session, user_id, station_id, actor=admin)


@router.post(
    "/platform/users/{user_id}/stations/{station_id}/delete-progress",
    response_model=schemas.StationProgressChange,
    responses=error_responses(
        Forbidden, errors.UserNotFound, errors.StationNotFound, errors.AttemptInProgress
    ),
)
async def delete_station_progress_for_support(
    user_id: uuid.UUID,
    station_id: uuid.UUID,
    body: schemas.DeleteStationProgress,
    admin: PlatformAdmin,
    session: Session,
) -> schemas.StationProgressChange:
    """Erase every attempt this person made at the station — transcript and
    marking with it — and take it out of their practice sets. Not undoable."""
    return await service_platform.delete_progress(
        session, user_id, station_id, reason=body.reason, actor=admin
    )
