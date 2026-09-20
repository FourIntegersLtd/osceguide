from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.tenancy import OrgAdmin, OrgReader
from app.features.stations import errors, schemas, service

router = APIRouter(tags=["stations"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/stations",
    response_model=Page[schemas.LibraryStationRead],
    responses=error_responses(Unauthenticated, errors.UnknownExamError),
)
async def browse_library(
    principal: CurrentPrincipal,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    exam_code: Annotated[str | None, Query()] = None,
) -> Page[schemas.LibraryStationRead]:
    items, next_cursor = await service.browse_library(
        session,
        exam_code=exam_code,
        limit=page.limit,
        cursor=page.cursor,
        all_exams=principal.is_platform_admin,
    )
    return Page(items=items, next_cursor=next_cursor)


@router.get(
    "/orgs/{org_slug}/stations",
    response_model=Page[schemas.StationRead],
    responses=error_responses(Forbidden),
)
async def list_stations(
    workspace: OrgReader, session: Session, page: Annotated[CursorParams, Depends()]
) -> Page[schemas.StationRead]:
    items, next_cursor = await service.list_stations(
        session, workspace.org_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=items, next_cursor=next_cursor)


@router.post(
    "/orgs/{org_slug}/stations",
    response_model=schemas.StationRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.UnknownExamError),
)
async def create_station(
    body: schemas.CreateStation, workspace: OrgAdmin, session: Session
) -> schemas.StationRead:
    return await service.create_station(
        session, workspace.org_id, title=body.title, exam_code=body.exam_code, content=body.content
    )


@router.post(
    "/orgs/{org_slug}/stations/{station_id}/versions",
    response_model=schemas.StationVersionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.StationNotFound),
)
async def add_version(
    station_id: uuid.UUID, workspace: OrgAdmin, session: Session
) -> schemas.StationVersionRead:
    return await service.add_version(session, workspace.org_id, station_id)


@router.patch(
    "/orgs/{org_slug}/stations/{station_id}/versions/{version}",
    response_model=schemas.StationVersionRead,
    responses=error_responses(Forbidden, errors.VersionNotFound, errors.NotEditableError),
)
async def edit_version(
    station_id: uuid.UUID,
    version: int,
    body: schemas.UpdateVersion,
    workspace: OrgAdmin,
    session: Session,
) -> schemas.StationVersionRead:
    return await service.edit_version(session, workspace.org_id, station_id, version, content=body.content)


@router.post(
    "/orgs/{org_slug}/stations/{station_id}/versions/{version}/publish",
    response_model=schemas.StationVersionRead,
    responses=error_responses(Forbidden, errors.VersionNotFound, errors.AlreadyPublishedError),
)
async def publish_version(
    station_id: uuid.UUID, version: int, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.StationVersionRead:
    return await service.publish_version(
        session,
        workspace.org_id,
        station_id,
        version,
        actor_id=workspace.principal.user_id,
        now=clock.now(),
    )


@router.post(
    "/orgs/{org_slug}/stations/{station_id}/versions/{version}/archive",
    response_model=schemas.StationVersionRead,
    responses=error_responses(Forbidden, errors.VersionNotFound, errors.NotArchivableError),
)
async def archive_version(
    station_id: uuid.UUID, version: int, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.StationVersionRead:
    return await service.archive_version(
        session,
        workspace.org_id,
        station_id,
        version,
        actor_id=workspace.principal.user_id,
        now=clock.now(),
    )
