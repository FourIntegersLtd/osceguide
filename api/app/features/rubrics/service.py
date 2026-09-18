"""Authoring a rubric: writing one, versioning it, publishing it.

A rubric follows the same draft/publish/archive lifecycle as everything else
that is versioned (`app.core.lifecycle`), for the same reason: a published
version is what somebody was marked against, so correcting it means a new
version rather than an edit.

Using a rubric — taking the snapshot an attempt is marked against — is
`service_marking.py`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import lifecycle
from app.core.errors import AppError, raise_mapped
from app.features.rubrics import domain, errors, repository
from app.features.rubrics.models import Rubric, RubricVersion
from app.features.rubrics.schemas import RubricRead, RubricVersionRead

REFUSALS: dict[type[Exception], type[AppError]] = {
    lifecycle.NotEditable: errors.NotEditableError,
    lifecycle.AlreadyPublished: errors.AlreadyPublishedError,
    lifecycle.NotArchivable: errors.NotArchivableError,
    domain.InvalidRubric: errors.InvalidRubricError,
}


async def create_rubric(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    title: str,
    structure: dict[str, Any],
    system_prompt: str,
    pacing: dict[str, Any],
    result_schema_override: dict[str, Any] | None = None,
) -> RubricRead:
    """A rubric and its first draft version, ready to edit or publish."""
    parsed, checked_pacing = _validated(structure, pacing)
    rubric = await repository.create_rubric(session, org_id, title=title)
    version = await repository.add_version(
        session,
        org_id,
        rubric_id=rubric.id,
        version=1,
        structure=structure,
        system_prompt=system_prompt,
        pacing=checked_pacing,
        result_schema_override=result_schema_override,
    )
    return _rubric_read(rubric, [version])


async def list_rubrics(
    session: AsyncSession, org_id: uuid.UUID | None, *, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[RubricRead], str | None]:
    rubrics, next_cursor = await repository.list_rubrics(session, org_id, limit=limit, cursor=cursor)
    out = []
    for rubric in rubrics:
        versions = await repository.versions_for_rubric(session, org_id, rubric.id)
        out.append(_rubric_read(rubric, list(versions)))
    return out, next_cursor


async def read_rubric(session: AsyncSession, org_id: uuid.UUID | None, rubric_id: uuid.UUID) -> RubricRead:
    rubric = await repository.readable_rubric(session, org_id, rubric_id)
    if rubric is None:
        raise errors.RubricNotFound()
    versions = await repository.versions_for_rubric(session, org_id, rubric_id)
    return _rubric_read(rubric, list(versions))


async def add_version(
    session: AsyncSession, org_id: uuid.UUID | None, rubric_id: uuid.UUID
) -> RubricVersionRead:
    """A new draft, seeded from the latest published version.

    Not the latest version: an abandoned draft must not silently become the
    basis of everything after it.
    """
    rubric = await _own_rubric(session, org_id, rubric_id)
    existing = list(await repository.versions_for_rubric(session, org_id, rubric_id))
    refs = [lifecycle.VersionRef(number=v.version, status=lifecycle.Status(v.status)) for v in existing]
    seed = lifecycle.seed_version(refs)
    source = next((v for v in existing if seed and v.version == seed.number), None)
    version = await repository.add_version(
        session,
        org_id,
        rubric_id=rubric.id,
        version=lifecycle.next_version_number(refs),
        structure=dict(source.structure) if source else {},
        system_prompt=source.system_prompt if source else "",
        pacing=dict(source.pacing) if source else {},
        result_schema_override=dict(source.result_schema_override)
        if source and source.result_schema_override
        else None,
    )
    return _version_read(version)


async def edit_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    rubric_id: uuid.UUID,
    version: int,
    *,
    structure: dict[str, Any],
    system_prompt: str,
    pacing: dict[str, Any],
    result_schema_override: dict[str, Any] | None,
) -> RubricVersionRead:
    row = await _version(session, org_id, rubric_id, version)
    try:
        lifecycle.ensure_editable(
            lifecycle.VersionRef(number=row.version, status=lifecycle.Status(row.status))
        )
        parsed, checked_pacing = _validated(structure, pacing)
    except Exception as exc:  # noqa: BLE001 — mapped to the error carrying its status
        raise_mapped(exc, REFUSALS)
    await repository.set_version_body(
        session,
        org_id,
        row.id,
        structure=structure,
        system_prompt=system_prompt,
        pacing=checked_pacing,
        result_schema_override=result_schema_override,
    )
    await session.refresh(row)
    return _version_read(row)


async def publish_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    rubric_id: uuid.UUID,
    version: int,
    *,
    actor_id: uuid.UUID | None,
    now: datetime,
) -> RubricVersionRead:
    row = await _version(session, org_id, rubric_id, version)
    try:
        status = lifecycle.publish(
            lifecycle.VersionRef(number=row.version, status=lifecycle.Status(row.status))
        )
        # A rubric is only checked as hard as it is about to be used. Publishing
        # is that moment: after this the version is immutable and attempts will
        # be marked against it.
        domain.parse_structure(row.structure)
        domain.validate_pacing(row.pacing)
        if not (row.system_prompt or "").strip():
            raise domain.InvalidRubric("A rubric cannot be published without marking instructions.")
    except Exception as exc:  # noqa: BLE001
        raise_mapped(exc, REFUSALS)
    await repository.set_version_status(session, org_id, row.id, status=status, at=now, by=actor_id)
    await repository.set_current_version(session, org_id, rubric_id, version_id=row.id)
    await session.refresh(row)
    return _version_read(row)


async def archive_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    rubric_id: uuid.UUID,
    version: int,
    *,
    actor_id: uuid.UUID | None,
    now: datetime,
) -> RubricVersionRead:
    row = await _version(session, org_id, rubric_id, version)
    try:
        status = lifecycle.archive(
            lifecycle.VersionRef(number=row.version, status=lifecycle.Status(row.status))
        )
    except Exception as exc:  # noqa: BLE001
        raise_mapped(exc, REFUSALS)
    await repository.set_version_status(session, org_id, row.id, status=status, at=now, by=actor_id)
    await session.refresh(row)
    return _version_read(row)


def _validated(
    structure: dict[str, Any], pacing: dict[str, Any]
) -> tuple[domain.RubricStructure, dict[str, int]]:
    try:
        return domain.parse_structure(structure), domain.validate_pacing(pacing)
    except domain.InvalidRubric as exc:
        raise errors.InvalidRubricError(str(exc)) from exc


async def _own_rubric(session: AsyncSession, org_id: uuid.UUID | None, rubric_id: uuid.UUID) -> Rubric:
    rubric = await repository.rubric_by_id(session, org_id, rubric_id)
    if rubric is None:
        raise errors.RubricNotFound()
    return rubric


async def _version(
    session: AsyncSession, org_id: uuid.UUID | None, rubric_id: uuid.UUID, version: int
) -> RubricVersion:
    await _own_rubric(session, org_id, rubric_id)
    row = await repository.version_by_number(session, org_id, rubric_id, version)
    if row is None:
        raise errors.RubricVersionNotFound()
    return row


def _rubric_read(rubric: Rubric, versions: list[RubricVersion]) -> RubricRead:
    return RubricRead(
        id=rubric.id,
        owner_kind=rubric.owner_kind,
        org_id=rubric.org_id,
        title=rubric.title,
        current_version_id=rubric.current_version_id,
        versions=[_version_read(v) for v in versions],
    )


def _version_read(version: RubricVersion) -> RubricVersionRead:
    try:
        schema = domain.result_schema_for(
            domain.parse_structure(version.structure), version.result_schema_override
        )
    except domain.InvalidRubric:
        # A draft may be half-written. Showing an empty schema is better than
        # refusing to show the draft its author is in the middle of writing.
        schema = {}
    return RubricVersionRead(
        id=version.id,
        rubric_id=version.rubric_id,
        version=version.version,
        status=version.status,
        structure=dict(version.structure or {}),
        system_prompt=version.system_prompt,
        pacing=dict(version.pacing or {}),
        result_schema=schema,
        published_at=version.published_at,
    )
