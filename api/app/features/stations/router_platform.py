"""The platform's own station library, and the templates behind it.

The same services the org routes use, with `org_id=None`. Until now the
platform half of `stations` had no write path at all: the library was inserted
by a legacy import or by hand, and the four exams' station shapes lived in the
engine as formatters chosen by a branch on the exam's code.

An org may read and build on what is published here; only a platform admin may
write it. `OrgAdmin` sets `allow_platform_admin=False`, so the reverse holds
too — neither can author the other's content.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, InvalidInput, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.settings import SettingsDep
from app.core.tenancy import PlatformAdmin
from app.features.generation.errors import GenerationUnavailable
from app.features.stations import errors, schemas, service, service_templates, service_versions, station_autogenerate

router = APIRouter(tags=["stations"])

Session = Annotated[AsyncSession, Depends(get_session)]

_AUTH = (Unauthenticated, Forbidden)
_STATION = (errors.StationNotFound, errors.VersionNotFound)
_TEMPLATE = (errors.StationTemplateNotFound, errors.VersionNotFound)
_LIFECYCLE = (
    errors.NotEditableError,
    errors.AlreadyPublishedError,
    errors.NotArchivableError,
    errors.NotDeletableError,
)


# --- the library ------------------------------------------------------------


@router.get(
    "/platform/stations",
    response_model=Page[schemas.StationRead],
    responses=error_responses(*_AUTH),
)
async def list_platform_stations(
    admin: PlatformAdmin, session: Session, page: Annotated[CursorParams, Depends()]
) -> Page[schemas.StationRead]:
    """Every library station, drafts included — the author's own view of it."""
    items, next_cursor = await service.list_stations(session, None, limit=page.limit, cursor=page.cursor)
    return Page(items=items, next_cursor=next_cursor)


@router.post(
    "/platform/stations",
    response_model=schemas.StationRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        *_AUTH,
        errors.UnknownExamError,
        errors.StationTemplateVersionNotFound,
        errors.TemplateNotPublishedError,
    ),
)
async def create_platform_station(
    body: schemas.CreateStation, admin: PlatformAdmin, session: Session
) -> schemas.StationRead:
    return await service.create_station(
        session,
        None,
        title=body.title,
        exam_code=body.exam_code,
        content=body.content,
        template_version_id=body.template_version_id,
    )


@router.post(
    "/platform/stations/autogenerate-draft",
    response_model=schemas.AutogenerateStationDraftResult,
    responses=error_responses(
        *_AUTH,
        InvalidInput,
        GenerationUnavailable,
        errors.StationTemplateVersionNotFound,
        errors.TemplateNotPublishedError,
    ),
)
async def autogenerate_platform_station_draft(
    body: schemas.AutogenerateStationDraft,
    admin: PlatformAdmin,
    session: Session,
    settings: SettingsDep,
) -> schemas.AutogenerateStationDraftResult:
    _ = admin
    result = await station_autogenerate.autogenerate_station_draft(
        session,
        None,
        prompt=body.prompt,
        template_version_id=body.template_version_id,
        settings=settings,
    )
    return schemas.AutogenerateStationDraftResult(**result)


@router.post(
    "/platform/stations/{station_id}/versions",
    response_model=schemas.StationVersionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(*_AUTH, *_STATION),
)
async def add_platform_station_version(
    station_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.StationVersionRead:
    return await service_versions.add_version(session, None, station_id)


@router.patch(
    "/platform/stations/{station_id}/versions/{version}",
    response_model=schemas.StationVersionRead,
    responses=error_responses(*_AUTH, *_STATION, errors.NotEditableError),
)
async def edit_platform_station_version(
    station_id: uuid.UUID,
    version: int,
    body: schemas.UpdateVersion,
    admin: PlatformAdmin,
    session: Session,
) -> schemas.StationVersionRead:
    return await service_versions.edit_version(session, None, station_id, version, content=body.content)


@router.post(
    "/platform/stations/{station_id}/versions/{version}/publish",
    response_model=schemas.StationVersionRead,
    responses=error_responses(*_AUTH, *_STATION, *_LIFECYCLE),
)
async def publish_platform_station_version(
    station_id: uuid.UUID, version: int, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.StationVersionRead:
    """Publish it into the library, where every organisation may draw on it."""
    return await service_versions.publish_version(
        session, None, station_id, version, actor_id=admin.user_id, now=clock.now()
    )


@router.post(
    "/platform/stations/{station_id}/versions/{version}/archive",
    response_model=schemas.StationVersionRead,
    responses=error_responses(*_AUTH, *_STATION, *_LIFECYCLE),
)
async def archive_platform_station_version(
    station_id: uuid.UUID, version: int, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.StationVersionRead:
    return await service_versions.archive_version(
        session, None, station_id, version, actor_id=admin.user_id, now=clock.now()
    )


# --- the shapes behind it ---------------------------------------------------


@router.get(
    "/platform/station-templates",
    response_model=Page[schemas.StationTemplateRead],
    responses=error_responses(*_AUTH),
)
async def list_platform_station_templates(
    admin: PlatformAdmin, session: Session
) -> Page[schemas.StationTemplateRead]:
    return Page(items=await service_templates.list_templates(session, None), next_cursor=None)


@router.post(
    "/platform/station-templates",
    response_model=schemas.StationTemplateRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(*_AUTH, errors.UnknownExamError),
)
async def create_platform_station_template(
    body: schemas.CreateStationTemplate, admin: PlatformAdmin, session: Session
) -> schemas.StationTemplateRead:
    return await service_templates.create_template(
        session, None, title=body.title, exam_code=body.exam_code, structure=body.structure
    )


@router.post(
    "/platform/station-templates/{template_id}/versions",
    response_model=schemas.StationTemplateVersionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(*_AUTH, *_TEMPLATE),
)
async def add_platform_template_version(
    template_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.StationTemplateVersionRead:
    return await service_templates.add_version(session, None, template_id)


@router.patch(
    "/platform/station-templates/{template_id}/versions/{version}",
    response_model=schemas.StationTemplateVersionRead,
    responses=error_responses(*_AUTH, *_TEMPLATE, errors.NotEditableError),
)
async def edit_platform_template_version(
    template_id: uuid.UUID,
    version: int,
    body: schemas.UpdateStationTemplateVersion,
    admin: PlatformAdmin,
    session: Session,
) -> schemas.StationTemplateVersionRead:
    return await service_templates.edit_version(session, None, template_id, version, structure=body.structure)


@router.post(
    "/platform/station-templates/{template_id}/publish",
    response_model=schemas.StationTemplateVersionRead,
    responses=error_responses(*_AUTH, *_TEMPLATE, *_LIFECYCLE),
)
async def publish_platform_station_template(
    template_id: uuid.UUID, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.StationTemplateVersionRead:
    return await service_templates.publish_version(
        session, None, template_id, actor_id=admin.user_id, now=clock.now()
    )


@router.post(
    "/platform/station-templates/{template_id}/versions/{version}/archive",
    response_model=schemas.StationTemplateVersionRead,
    responses=error_responses(*_AUTH, *_TEMPLATE, *_LIFECYCLE),
)
async def archive_platform_station_template_version(
    template_id: uuid.UUID, version: int, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.StationTemplateVersionRead:
    return await service_templates.archive_version(
        session, None, template_id, version, actor_id=admin.user_id, now=clock.now()
    )


@router.delete(
    "/platform/station-templates/{template_id}/versions/{version}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(*_AUTH, *_TEMPLATE, *_LIFECYCLE),
)
async def delete_platform_station_template_version(
    template_id: uuid.UUID, version: int, admin: PlatformAdmin, session: Session
) -> None:
    await service_templates.delete_version(session, None, template_id, version)
