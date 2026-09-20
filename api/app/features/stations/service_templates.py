"""Station template authoring: the shape an organisation's stations take.

A template says what a station of this kind contains — which fields an author
fills in — and a station version may be built on a published one. The tables
existed with no repository, no service and no routes, so the column that binds
a station to its template could only ever be null, and T3 (`ensure_bindable`)
had nothing to refuse.

Same state machine as stations and rubrics (`domain.publish`,
`domain.ensure_editable`), which is why all three live in this slice.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput, raise_mapped
from app.features.stations.station_validator import (
    validate_generation_policy,
    validate_station_structure,
)
from app.features.catalog.errors import UnknownExamError as CatalogUnknownExam
from app.features.catalog.service import exam_code_by_id, resolve_exam
from app.features.stations import domain, errors
from app.features.stations import repository_templates as repository
from app.features.stations.models import StationTemplate, StationTemplateVersion
from app.features.stations.refusals import REFUSALS as _REFUSALS
from app.features.stations.schemas import StationTemplateRead, StationTemplateVersionRead


def _ensure_valid_structure(structure: dict[str, Any], *, org_id: uuid.UUID | None) -> None:
    ok, errs = validate_station_structure(structure)
    if not ok:
        raise InvalidInput(f"Template structure invalid: {errs}")
    policy_errs = validate_generation_policy(structure, org_id=org_id)
    if policy_errs:
        raise InvalidInput(f"Template generation settings invalid: {policy_errs}")


async def create_template(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    title: str,
    exam_code: str | None,
    structure: dict[str, Any],
) -> StationTemplateRead:
    """A template and its first draft version, ready to edit or publish."""
    _ensure_valid_structure(structure, org_id=org_id)
    exam_id = None
    code = None
    if exam_code:
        try:
            exam = await resolve_exam(session, exam_code, org_id=org_id)
        except CatalogUnknownExam as exc:
            raise errors.UnknownExamError(str(exc)) from exc
        exam_id, code = exam.id, exam.code
    template = await repository.create_template(session, org_id, exam_id=exam_id, title=title)
    version = await repository.add_template_version(
        session, org_id, template_id=template.id, version=1, structure=structure
    )
    return _template_read(template, code, [version])


async def list_templates(session: AsyncSession, org_id: uuid.UUID | None) -> list[StationTemplateRead]:
    out: list[StationTemplateRead] = []
    for template in await repository.templates_visible_to(session, org_id):
        versions = await repository.template_versions(session, org_id, template.id)
        out.append(_template_read(template, await _exam_code(session, template), versions))
    return out


async def add_version(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID
) -> StationTemplateVersionRead:
    """Open a new draft, seeded from the latest published version."""
    await _require_template(session, org_id, template_id)
    existing = await repository.template_versions(session, org_id, template_id)
    refs = [domain.VersionRef(number=v.version, status=domain.Status(v.status)) for v in existing]
    seed = domain.seed_version(refs)
    structure: dict[str, Any] = {}
    if seed is not None:
        structure = dict(next(v for v in existing if v.version == seed.number).structure)
    row = await repository.add_template_version(
        session,
        org_id,
        template_id=template_id,
        version=domain.next_version_number(refs),
        structure=structure,
    )
    return _version_read(row)


async def edit_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    template_id: uuid.UUID,
    version: int,
    *,
    structure: dict[str, Any],
) -> StationTemplateVersionRead:
    row = await _version(session, org_id, template_id, version)
    try:
        domain.ensure_editable(domain.VersionRef(number=row.version, status=domain.Status(row.status)))
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    _ensure_valid_structure(structure, org_id=org_id)
    await repository.set_template_version_structure(session, org_id, row.id, structure=structure)
    return _version_read(await _version(session, org_id, template_id, version))


async def publish_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    template_id: uuid.UUID,
    *,
    actor_id: uuid.UUID,
    now: datetime,
) -> StationTemplateVersionRead:
    """Publish the newest version, which is then what a station may be built on."""
    await _require_template(session, org_id, template_id)
    versions = await repository.template_versions(session, org_id, template_id)
    if not versions:
        raise errors.VersionNotFound()
    latest = max(versions, key=lambda v: v.version)
    try:
        status = domain.publish(domain.VersionRef(number=latest.version, status=domain.Status(latest.status)))
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.set_template_version_status(
        session, org_id, latest.id, status=str(status), at=now, by=actor_id
    )
    return _version_read(await _version(session, org_id, template_id, latest.version))


async def archive_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    template_id: uuid.UUID,
    version: int,
    *,
    actor_id: uuid.UUID,
    now: datetime,
) -> StationTemplateVersionRead:
    row = await _version(session, org_id, template_id, version)
    try:
        new_status = domain.archive(domain.VersionRef(number=row.version, status=domain.Status(row.status)))
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.set_template_version_status(
        session, org_id, row.id, status=str(new_status), at=now, by=actor_id
    )
    return _version_read(await _version(session, org_id, template_id, version))


async def delete_version(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID, version: int
) -> None:
    """Throw away a draft. When it was the template's only row, remove the template too."""
    row = await _version(session, org_id, template_id, version)
    try:
        domain.ensure_deletable(domain.VersionRef(number=row.version, status=domain.Status(row.status)))
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.delete_template_version(session, org_id, row.id)
    if not await repository.template_versions(session, org_id, template_id):
        await repository.delete_template(session, org_id, template_id)


async def bindable_version(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> StationTemplateVersion:
    """The template version a station may be built on (T3).

    Raises if it is missing, belongs to another organisation, or is still a
    draft. The rule was written and unit-tested with nothing to call it, so a
    station could have been built on a shape somebody was still deciding.
    """
    row = await repository.bindable_template_version(session, org_id, version_id)
    if row is None:
        raise errors.StationTemplateVersionNotFound()
    try:
        domain.ensure_bindable(domain.VersionRef(number=row.version, status=domain.Status(row.status)))
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    return row


async def _require_template(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID
) -> StationTemplate:
    row = await repository.template_by_id(session, org_id, template_id)
    if row is None:
        raise errors.StationTemplateNotFound()
    return row


async def _version(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID, version: int
) -> StationTemplateVersion:
    await _require_template(session, org_id, template_id)
    for row in await repository.template_versions(session, org_id, template_id):
        if row.version == version:
            return row
    raise errors.VersionNotFound()


async def _exam_code(session: AsyncSession, template: StationTemplate) -> str | None:
    if template.exam_id is None:
        return None
    return await exam_code_by_id(session, template.exam_id)


def _template_read(
    template: StationTemplate, exam_code: str | None, versions: list[StationTemplateVersion]
) -> StationTemplateRead:
    return StationTemplateRead(
        id=template.id,
        title=template.title,
        exam_code=exam_code,
        versions=[_version_read(v) for v in versions],
    )


def _version_read(row: StationTemplateVersion) -> StationTemplateVersionRead:
    return StationTemplateVersionRead(
        id=row.id,
        template_id=row.template_id,
        version=row.version,
        status=row.status,
        structure=dict(row.structure),
        published_at=row.published_at,
    )
