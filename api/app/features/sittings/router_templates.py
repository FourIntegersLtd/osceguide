"""Exam templates: save a schedule's setup under a name and start new schedules from it."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.core.db import SessionDep as Session
from app.core.errors import Forbidden, error_responses
from app.core.tenancy import OrgAdmin
from app.features.sittings import errors, schemas, service_templates

router = APIRouter(tags=["sittings"])


# Org admin only, the same people who may schedule a sitting (`schedule_sittings`).
@router.get(
    "/orgs/{org_slug}/sitting-templates",
    response_model=list[schemas.TemplateRead],
    responses=error_responses(Forbidden),
)
async def list_templates(workspace: OrgAdmin, session: Session) -> list[schemas.TemplateRead]:
    return await service_templates.list_templates(session, workspace.org_id)


# Save a schedule's setup under a name.
@router.post(
    "/orgs/{org_slug}/sitting-templates",
    response_model=schemas.TemplateRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.TemplateNameTaken),
)
async def create_template(
    body: schemas.CreateTemplate, workspace: OrgAdmin, session: Session
) -> schemas.TemplateRead:
    return await service_templates.create_template(
        session, workspace.org_id, workspace.principal.user_id, body
    )


# Rename a saved template.
@router.put(
    "/orgs/{org_slug}/sitting-templates/{template_id}",
    response_model=schemas.TemplateRead,
    responses=error_responses(Forbidden, errors.TemplateNotFound, errors.TemplateNameTaken),
)
async def rename_template(
    template_id: uuid.UUID, body: schemas.RenameTemplate, workspace: OrgAdmin, session: Session
) -> schemas.TemplateRead:
    return await service_templates.rename_template(session, workspace.org_id, template_id, body.name)


# Forget a saved template; sittings already made from it are unaffected.
@router.delete(
    "/orgs/{org_slug}/sitting-templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Forbidden, errors.TemplateNotFound),
)
async def remove_template(template_id: uuid.UUID, workspace: OrgAdmin, session: Session) -> None:
    await service_templates.remove_template(session, workspace.org_id, template_id, workspace.principal)
