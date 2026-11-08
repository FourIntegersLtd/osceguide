"""Named schedule setups an organisation keeps (exam templates).

A template holds the setup only (stations, mode, timing, assessor style), never people or a
date, so applying one cannot leak who sat what. Every read and write is scoped to the org.
"""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.sittings import errors, repository_templates, schemas
from app.features.sittings.models import SittingTemplate
from app.features.tenancy import service_audit as audit


def _read(row: SittingTemplate) -> schemas.TemplateRead:
    """A stored template as the api speaks it."""
    return schemas.TemplateRead(
        id=row.id,
        name=row.name,
        config=schemas.TemplateConfig.model_validate(row.config),
        created_at=row.created_at,
    )


async def _require(session: AsyncSession, org_id: uuid.UUID, template_id: uuid.UUID) -> SittingTemplate:
    """The template, or `template_not_found` when it is missing or another organisation's."""
    row = await repository_templates.find(session, org_id, template_id)
    if row is None:
        raise errors.TemplateNotFound()
    return row


async def _refuse_taken(
    session: AsyncSession, org_id: uuid.UUID, name: str, *, besides: uuid.UUID | None
) -> None:
    """Refuse a name another template here already has, so the list never shows two alike."""
    if await repository_templates.name_in_use(session, org_id, name, besides=besides):
        raise errors.TemplateNameTaken()


async def list_templates(session: AsyncSession, org_id: uuid.UUID) -> list[schemas.TemplateRead]:
    """Every template the organisation has saved, by name."""
    return [_read(row) for row in await repository_templates.list_for_org(session, org_id)]


async def create_template(
    session: AsyncSession, org_id: uuid.UUID, actor_id: uuid.UUID | None, body: schemas.CreateTemplate
) -> schemas.TemplateRead:
    """Save a setup under a name nobody else here is using."""
    await _refuse_taken(session, org_id, body.name, besides=None)
    try:
        row = await repository_templates.add(
            session, org_id, name=body.name, config=body.config.model_dump(mode="json"), created_by=actor_id
        )
    except IntegrityError as clash:  # a concurrent save of the same name
        raise errors.TemplateNameTaken() from clash
    return _read(row)


async def rename_template(
    session: AsyncSession, org_id: uuid.UUID, template_id: uuid.UUID, name: str
) -> schemas.TemplateRead:
    """Change a template's name, keeping names unique within the organisation."""
    row = await _require(session, org_id, template_id)
    await _refuse_taken(session, org_id, name, besides=template_id)
    try:
        renamed = await repository_templates.rename(session, row, name)
    except IntegrityError as clash:  # a concurrent rename to the same name
        raise errors.TemplateNameTaken() from clash
    return _read(renamed)


async def remove_template(
    session: AsyncSession, org_id: uuid.UUID, template_id: uuid.UUID, actor: Principal
) -> None:
    """Forget a template. Sittings made from it are untouched: they copied the setup, not a link."""
    row = await _require(session, org_id, template_id)
    await repository_templates.remove(session, org_id, template_id)
    await audit.record_for_owner(
        session,
        org_id=org_id,
        actor=actor,
        action="sitting_template.removed",
        target_type="sitting_template",
        target_id=str(template_id),
        summary=f'Removed the template "{row.name}"',
    )
