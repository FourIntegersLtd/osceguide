"""Reporting a station, and working the queue of reports.

`/me/station-flags` is the reader's half and `/platform/station-flags` the
content team's. They live together because they are one feature with two
audiences, and apart from `router.py` because that file is the authoring surface
— versions, publishing, lifecycle — and this is feedback about the result.

The report route used to be served by `identity` with the body discarded and a
docstring saying persistence is TODO. The button stayed on the screen either
way, which is the worst version of an unimplemented feature: it answers.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.tenancy import PlatformAdmin
from app.features.stations import errors, schemas, service_flags

router = APIRouter(tags=["stations"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/me/station-flags",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Unauthenticated, errors.StationNotFound),
)
async def report_station(
    body: schemas.FlagStationBody, principal: CurrentPrincipal, session: Session
) -> Response:
    """Report one station the caller can see as wrong.

    Idempotent: reporting the same station twice is the same report, not a
    duplicate and not an error.
    """
    await service_flags.report(session, station_id=body.station_id, user_id=principal.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me/station-flags",
    response_model=list[schemas.StationFlagRead],
    responses=error_responses(Unauthenticated),
)
async def my_reports(principal: CurrentPrincipal, session: Session) -> list[schemas.StationFlagRead]:
    """What this person has reported, so the runner's button and the list agree."""
    return await service_flags.my_reports(session, principal.user_id)


@router.get(
    "/platform/station-flags",
    response_model=Page[schemas.StationFlagRead],
    responses=error_responses(Unauthenticated, Forbidden),
)
async def station_flag_queue(
    admin: PlatformAdmin,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    report_status: Annotated[str | None, Query(alias="status", pattern="^(open|resolved)$")] = None,
) -> Page[schemas.StationFlagRead]:
    """Every report on every station, oldest first. `status=open` is the queue.

    Named `report_status` in Python because `status` is FastAPI's own import
    here; the query parameter stays `status`, which is what a client reads.
    """
    items, next_cursor = await service_flags.queue(
        session, status=report_status, limit=page.limit, cursor=page.cursor
    )
    return Page(items=items, next_cursor=next_cursor)


@router.patch(
    "/platform/station-flags/{flag_id}",
    response_model=schemas.StationFlagRead,
    responses=error_responses(Unauthenticated, Forbidden, errors.StationFlagNotFound),
)
async def decide_station_flag(
    flag_id: uuid.UUID,
    body: schemas.UpdateStationFlag,
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.StationFlagRead:
    """Close a report with a note, or reopen a closed one."""
    return await service_flags.decide(session, flag_id, body=body, actor_id=admin.user_id, now=clock.now())
