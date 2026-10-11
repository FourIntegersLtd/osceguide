"""Station template routes: the shape an organisation's stations take.

A router of its own, like `router_feedback.py`, along the aggregate. Same tag,
so the generated client still groups the slice together.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.db import SessionDep as Session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.tenancy import OrgAdmin, OrgStaff
from app.features.stations import errors, schemas, service_templates

router = APIRouter(tags=["stations"])


# This org's own templates and the platform's.
@router.get(
    "/orgs/{org_slug}/station-templates",
    response_model=Page[schemas.StationTemplateRead],
    responses=error_responses(Forbidden),
)
async def list_station_templates(
    workspace: OrgStaff,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    search: str | None = None,
    exam_code: str | None = None,
    published_only: bool = False,
) -> Page[schemas.StationTemplateRead]:
    templates, next_cursor = await service_templates.list_templates(
        session,
        workspace.org_id,
        limit=page.limit,
        cursor=page.cursor,
        search=search,
        exam_code=exam_code,
        published_only=published_only,
    )
    return Page(items=templates, next_cursor=next_cursor)


# Author a new template owned by this org.
@router.post(
    "/orgs/{org_slug}/station-templates",
    response_model=schemas.StationTemplateRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.UnknownExamError),
)
async def create_station_template(
    body: schemas.CreateStationTemplate, workspace: OrgAdmin, session: Session
) -> schemas.StationTemplateRead:
    return await service_templates.create_template(
        session,
        workspace.org_id,
        title=body.title,
        exam_code=body.exam_code,
        structure=body.structure,
    )


@router.post(
    "/orgs/{org_slug}/station-templates/{template_id}/versions",
    response_model=schemas.StationTemplateVersionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.StationTemplateNotFound),
)
async def add_station_template_version(
    template_id: uuid.UUID, workspace: OrgAdmin, session: Session
) -> schemas.StationTemplateVersionRead:
    """A new draft, seeded from the latest published version."""
    return await service_templates.add_version(session, workspace.org_id, template_id)


# Overwrite a draft template version's structure.
@router.patch(
    "/orgs/{org_slug}/station-templates/{template_id}/versions/{version}",
    response_model=schemas.StationTemplateVersionRead,
    responses=error_responses(
        Forbidden,
        errors.StationTemplateNotFound,
        errors.VersionNotFound,
        errors.NotEditableError,
    ),
)
async def edit_station_template_version(
    template_id: uuid.UUID,
    version: int,
    body: schemas.UpdateStationTemplateVersion,
    workspace: OrgAdmin,
    session: Session,
) -> schemas.StationTemplateVersionRead:
    return await service_templates.edit_version(
        session, workspace.org_id, template_id, version, structure=body.structure, title=body.title
    )


@router.post(
    "/orgs/{org_slug}/station-templates/{template_id}/publish",
    response_model=schemas.StationTemplateVersionRead,
    responses=error_responses(
        Forbidden,
        errors.StationTemplateNotFound,
        errors.VersionNotFound,
        errors.AlreadyPublishedError,
        errors.NotEditableError,
    ),
)
async def publish_station_template(
    template_id: uuid.UUID, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.StationTemplateVersionRead:
    """Publishes the template's newest version, which stations may then be built on."""
    return await service_templates.publish_version(
        session, workspace.org_id, template_id, actor_id=workspace.principal.user_id, now=clock.now()
    )


# Take the organisation's own editable copy of a platform template.
@router.post(
    "/orgs/{org_slug}/station-templates/{template_id}/copy",
    response_model=schemas.StationTemplateRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        Forbidden,
        errors.StationTemplateNotFound,
        errors.TemplateNotPublishedError,
        errors.UnknownExamError,
    ),
)
async def copy_station_template(
    template_id: uuid.UUID, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.StationTemplateRead:
    """Copies a platform template's published version into this org, published and ready to use."""
    return await service_templates.copy_template(
        session, workspace.org_id, template_id, actor_id=workspace.principal.user_id, now=clock.now()
    )


# Retire a published template version.
@router.post(
    "/orgs/{org_slug}/station-templates/{template_id}/versions/{version}/archive",
    response_model=schemas.StationTemplateVersionRead,
    responses=error_responses(
        Forbidden,
        errors.StationTemplateNotFound,
        errors.VersionNotFound,
        errors.NotArchivableError,
    ),
)
async def archive_station_template_version(
    template_id: uuid.UUID,
    version: int,
    workspace: OrgAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.StationTemplateVersionRead:
    return await service_templates.archive_version(
        session,
        workspace.org_id,
        template_id,
        version,
        actor_id=workspace.principal.user_id,
        now=clock.now(),
    )


@router.delete(
    "/orgs/{org_slug}/station-templates/{template_id}/versions/{version}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(
        Forbidden,
        errors.StationTemplateNotFound,
        errors.VersionNotFound,
        errors.NotDeletableError,
    ),
)
async def delete_station_template_version(
    template_id: uuid.UUID, version: int, workspace: OrgAdmin, session: Session
) -> None:
    """Throw away a draft. A published version is what stations may have been built on."""
    await service_templates.delete_version(session, workspace.org_id, template_id, version)
