"""Platform-owned station templates."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.db import SessionDep as Session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.tenancy import PlatformAdmin
from app.features.stations import errors, schemas, service_templates

router = APIRouter(tags=["stations"])


_AUTH = (Unauthenticated, Forbidden)
_TEMPLATE = (errors.StationTemplateNotFound, errors.VersionNotFound)
_LIFECYCLE = (
    errors.NotEditableError,
    errors.AlreadyPublishedError,
    errors.NotArchivableError,
    errors.NotDeletableError,
)


# The platform's own templates, a page at a time.
@router.get(
    "/platform/station-templates",
    response_model=Page[schemas.StationTemplateRead],
    responses=error_responses(*_AUTH),
)
async def list_platform_station_templates(
    admin: PlatformAdmin,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    search: str | None = None,
    exam_code: str | None = None,
    published_only: bool = False,
) -> Page[schemas.StationTemplateRead]:
    templates, next_cursor = await service_templates.list_templates(
        session,
        None,
        limit=page.limit,
        cursor=page.cursor,
        search=search,
        exam_code=exam_code,
        published_only=published_only,
    )
    return Page(items=templates, next_cursor=next_cursor)


# Author a new platform-owned template.
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


# Add a new version to a platform station template.
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


# Overwrite a draft template version's structure.
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


# Publish the template's newest version, which stations may then be built on.
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


# Retire a published template version.
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


# Delete one version of a platform station template.
@router.delete(
    "/platform/station-templates/{template_id}/versions/{version}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(*_AUTH, *_TEMPLATE, *_LIFECYCLE),
)
async def delete_platform_station_template_version(
    template_id: uuid.UUID, version: int, admin: PlatformAdmin, session: Session
) -> None:
    await service_templates.delete_version(session, None, template_id, version)
