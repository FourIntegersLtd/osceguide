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
from app.features.catalog.errors import UnknownExamError as CatalogUnknownExam
from app.features.catalog.service import exam_code_by_id, resolve_exam
from app.features.stations import domain, errors
from app.features.stations import repository_templates as repository
from app.features.stations.models import StationTemplate, StationTemplateVersion
from app.features.stations.refusals import REFUSALS as _REFUSALS
from app.features.stations.schemas import StationTemplateRead, StationTemplateVersionRead
from app.features.stations.station_validator import (
    validate_generation_policy,
    validate_station_structure,
)


def _ensure_valid_structure(structure: dict[str, Any]) -> None:
    """Refuse a template structure whose fields, or generation settings, do not hold up."""
    is_valid, structure_errors = validate_station_structure(structure)
    if not is_valid:
        raise InvalidInput(f"Template structure invalid: {structure_errors}")
    policy_errors = validate_generation_policy(structure)
    if policy_errors:
        raise InvalidInput(f"Template generation settings invalid: {policy_errors}")


async def create_template(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    title: str,
    exam_code: str | None,
    structure: dict[str, Any],
) -> StationTemplateRead:
    """A template and its first draft version, ready to edit or publish."""
    _ensure_valid_structure(structure)
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


async def list_templates(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    limit: int,
    cursor: dict[str, Any] | None,
    search: str | None = None,
    exam_code: str | None = None,
    published_only: bool = False,
) -> tuple[list[StationTemplateRead], str | None]:
    """A page of this org's own templates and the platform's, each with all its versions.

    `search` is a title fragment. `exam_code`, when given, matches templates written for that exam
    plus every exam-agnostic template; a code this owner may not resolve answers an empty page rather
    than a catalogue error, since this is a list filter, not authoring input. `published_only` keeps
    only templates with at least one published version.
    """
    exam_id = None
    if exam_code is not None:
        try:
            exam_id = (await resolve_exam(session, exam_code, org_id=org_id)).id
        except CatalogUnknownExam:
            return [], None
    templates, next_cursor = await repository.templates_visible_to(
        session,
        org_id,
        limit=limit,
        cursor=cursor,
        search=search,
        exam_id=exam_id,
        published_only=published_only,
    )
    templates_read: list[StationTemplateRead] = []
    for template in templates:
        versions = await repository.template_versions(session, org_id, template.id)
        templates_read.append(_template_read(template, await _exam_code(session, template), versions))
    return templates_read, next_cursor


async def add_version(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID
) -> StationTemplateVersionRead:
    """Open a new draft, seeded from the latest published version."""
    await _require_template(session, org_id, template_id)
    existing = await repository.template_versions(session, org_id, template_id)
    refs = [
        domain.VersionRef(number=version.version, status=domain.Status(version.status))
        for version in existing
    ]
    seed = domain.seed_version(refs)
    structure: dict[str, Any] = {}
    if seed is not None:
        structure = dict(next(version for version in existing if version.version == seed.number).structure)
    template_version = await repository.add_template_version(
        session,
        org_id,
        template_id=template_id,
        version=domain.next_version_number(refs),
        structure=structure,
    )
    return _version_read(template_version)


async def edit_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    template_id: uuid.UUID,
    version: int,
    *,
    structure: dict[str, Any],
    title: str | None = None,
) -> StationTemplateVersionRead:
    """Overwrite a draft template version's structure, and the template's title if given."""
    template_version = await _version(session, org_id, template_id, version)
    try:
        domain.ensure_editable(
            domain.VersionRef(number=template_version.version, status=domain.Status(template_version.status))
        )
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    _ensure_valid_structure(structure)
    if title is not None:
        await repository.set_template_title(session, org_id, template_id, title=title)
    await repository.set_template_version_structure(session, org_id, template_version.id, structure=structure)
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
    latest = max(versions, key=lambda version: version.version)
    try:
        status = domain.publish(domain.VersionRef(number=latest.version, status=domain.Status(latest.status)))
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.set_template_version_status(
        session, org_id, latest.id, status=str(status), at=now, by=actor_id
    )
    return _version_read(await _version(session, org_id, template_id, latest.version))


async def copy_template(
    session: AsyncSession,
    org_id: uuid.UUID,
    template_id: uuid.UUID,
    *,
    actor_id: uuid.UUID,
    now: datetime,
) -> StationTemplateRead:
    """Give an organisation its own published copy of a platform template.

    The copy is the organisation's from then on: it edits and versions it like
    a template it wrote, and later changes to the platform's original do not
    reach it. Refused when the platform has no such template, or has not
    published it.
    """
    source = await _require_template(session, None, template_id)
    published = [
        version
        for version in await repository.template_versions(session, None, template_id)
        if version.status == "published"
    ]
    if not published:
        raise errors.TemplateNotPublishedError()
    copy = await create_template(
        session,
        org_id,
        title=source.title,
        exam_code=await _exam_code(session, source),
        structure=dict(published[-1].structure),
    )
    version = await publish_version(session, org_id, copy.id, actor_id=actor_id, now=now)
    return copy.model_copy(update={"versions": [version]})


async def archive_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    template_id: uuid.UUID,
    version: int,
    *,
    actor_id: uuid.UUID,
    now: datetime,
) -> StationTemplateVersionRead:
    """Retire a published template version so no new station may be built on it."""
    template_version = await _version(session, org_id, template_id, version)
    try:
        new_status = domain.archive(
            domain.VersionRef(number=template_version.version, status=domain.Status(template_version.status))
        )
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.set_template_version_status(
        session, org_id, template_version.id, status=str(new_status), at=now, by=actor_id
    )
    return _version_read(await _version(session, org_id, template_id, version))


async def delete_version(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID, version: int
) -> None:
    """Throw away a draft. When it was the template's only version, remove the template too."""
    template_version = await _version(session, org_id, template_id, version)
    try:
        domain.ensure_deletable(
            domain.VersionRef(number=template_version.version, status=domain.Status(template_version.status))
        )
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.delete_template_version(session, org_id, template_version.id)
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
    template_version = await repository.bindable_template_version(session, org_id, version_id)
    if template_version is None:
        raise errors.StationTemplateVersionNotFound()
    try:
        domain.ensure_bindable(
            domain.VersionRef(number=template_version.version, status=domain.Status(template_version.status))
        )
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    return template_version


async def _require_template(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID
) -> StationTemplate:
    """This org's template by id, or refuse if there is no such template."""
    template = await repository.template_by_id(session, org_id, template_id)
    if template is None:
        raise errors.StationTemplateNotFound()
    return template


async def _version(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID, version: int
) -> StationTemplateVersion:
    """One numbered version of this org's template, or refuse if there is no such version."""
    await _require_template(session, org_id, template_id)
    for template_version in await repository.template_versions(session, org_id, template_id):
        if template_version.version == version:
            return template_version
    raise errors.VersionNotFound()


async def _exam_code(session: AsyncSession, template: StationTemplate) -> str | None:
    """The exam code this template's exam id resolves to, or `None` for an exam-agnostic template."""
    if template.exam_id is None:
        return None
    return await exam_code_by_id(session, template.exam_id)


def _template_read(
    template: StationTemplate, exam_code: str | None, versions: list[StationTemplateVersion]
) -> StationTemplateRead:
    """Map a template and its versions onto the schema."""
    return StationTemplateRead(
        id=template.id,
        title=template.title,
        owner_kind=template.owner_kind,
        exam_code=exam_code,
        versions=[_version_read(version) for version in versions],
    )


def _version_read(template_version: StationTemplateVersion) -> StationTemplateVersionRead:
    """Map a template version onto the schema."""
    return StationTemplateVersionRead(
        id=template_version.id,
        template_id=template_version.template_id,
        version=template_version.version,
        status=template_version.status,
        structure=dict(template_version.structure),
        published_at=template_version.published_at,
    )
