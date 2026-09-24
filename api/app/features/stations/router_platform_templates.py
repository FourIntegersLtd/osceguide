"""Platform-owned station templates."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.pagination import Page
from app.core.ports import ClockDep
from app.core.tenancy import PlatformAdmin
from app.features.stations import errors, schemas, service_templates

router = APIRouter(tags=["stations"])

Session = Annotated[AsyncSession, Depends(get_session)]

_AUTH = (Unauthenticated, Forbidden)
_TEMPLATE = (errors.StationTemplateNotFound, errors.VersionNotFound)
_LIFECYCLE = (
    errors.NotEditableError,
    errors.AlreadyPublishedError,
    errors.NotArchivableError,
    errors.NotDeletableError,
)


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
    return await service_templates.edit_version(
        session, None, template_id, version, structure=body.structure, title=body.title
    )


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
