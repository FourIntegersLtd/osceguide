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
from app.features.catalog import service as catalog_service
from app.features.catalog.errors import UnknownExamError as CatalogUnknownExam
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
    marking_layout: dict[str, Any] | None = None,
) -> RubricRead:
    """A rubric and its first draft version, ready to edit or publish."""
    parsed, checked_pacing = validated(structure, pacing)
    validate_marking_layout(marking_layout)
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
        marking_layout=marking_layout,
    )
    return rubric_read(rubric, [version])


async def list_rubrics(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    search: str | None = None,
    exam_code: str | None = None,
) -> tuple[list[RubricRead], str | None]:
    """This owner's rubrics, each with all of its versions, one page at a time.

    `search` matches a rubric's title; `exam_code` narrows to rubrics bound to
    one exam, so an author picking a rubric for an exam sees only candidates.
    An unresolvable `exam_code` is treated as no match, since this is a list
    filter, not authoring input.
    """
    rubric_version_id = None
    if exam_code:
        try:
            exam = await catalog_service.resolve_exam(session, exam_code, org_id=org_id)
        except CatalogUnknownExam:
            return [], None
        rubric_version_id = exam.rubric_version_id
        if rubric_version_id is None:
            return [], None
    rubrics, next_cursor = await repository.list_rubrics(
        session, org_id, limit=limit, cursor=cursor, search=search, rubric_version_id=rubric_version_id
    )
    rubric_reads = []
    for rubric in rubrics:
        versions = await repository.versions_for_rubric(session, org_id, rubric.id)
        rubric_reads.append(rubric_read(rubric, list(versions)))
    return rubric_reads, next_cursor


async def read_rubric(session: AsyncSession, org_id: uuid.UUID | None, rubric_id: uuid.UUID) -> RubricRead:
    """One rubric and all of its versions, or the refusal if it is unknown."""
    rubric = await repository.readable_rubric(session, org_id, rubric_id)
    if rubric is None:
        raise errors.RubricNotFound()
    versions = await repository.versions_for_rubric(session, org_id, rubric_id)
    return rubric_read(rubric, list(versions))


async def add_version(
    session: AsyncSession, org_id: uuid.UUID | None, rubric_id: uuid.UUID
) -> RubricVersionRead:
    """A new draft, seeded from the latest published version.

    Not the latest version: an abandoned draft must not silently become the
    basis of everything after it.
    """
    rubric = await _own_rubric(session, org_id, rubric_id)
    existing = list(await repository.versions_for_rubric(session, org_id, rubric_id))
    refs = [
        lifecycle.VersionRef(number=version_row.version, status=lifecycle.Status(version_row.status))
        for version_row in existing
    ]
    seed = lifecycle.seed_version(refs)
    source = next(
        (version_row for version_row in existing if seed and version_row.version == seed.number), None
    )
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
        marking_layout=dict(source.marking_layout) if source and source.marking_layout else None,
    )
    return version_read(version)


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
    marking_layout: dict[str, Any] | None,
) -> RubricVersionRead:
    """Rewrite a draft's body. Refused as `not_editable` once it has been published."""
    version_row = await _version(session, org_id, rubric_id, version)
    try:
        lifecycle.ensure_editable(
            lifecycle.VersionRef(number=version_row.version, status=lifecycle.Status(version_row.status))
        )
        parsed, checked_pacing = validated(structure, pacing)
        validate_marking_layout(marking_layout)
    except Exception as exc:  # noqa: BLE001 — mapped to the error carrying its status
        raise_mapped(exc, REFUSALS)
    await repository.set_version_body(
        session,
        org_id,
        version_row.id,
        structure=structure,
        system_prompt=system_prompt,
        pacing=checked_pacing,
        result_schema_override=result_schema_override,
        marking_layout=marking_layout,
    )
    await session.refresh(version_row)
    return version_read(version_row)


async def publish_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    rubric_id: uuid.UUID,
    version: int,
    *,
    actor_id: uuid.UUID | None,
    now: datetime,
) -> RubricVersionRead:
    """Make this version the one new attempts are marked against.

    Refuses a structure that cannot be parsed, pacing that cannot be run, an
    empty system prompt, and a platform rubric with no examiner marking layout.
    """
    version_row = await _version(session, org_id, rubric_id, version)
    try:
        status = lifecycle.publish(
            lifecycle.VersionRef(number=version_row.version, status=lifecycle.Status(version_row.status))
        )
        # A rubric is only checked as hard as it is about to be used. Publishing
        # is that moment: after this the version is immutable and attempts will
        # be marked against it.
        domain.parse_structure(version_row.structure)
        domain.validate_pacing(version_row.pacing)
        if not (version_row.system_prompt or "").strip():
            raise domain.InvalidRubric("A rubric cannot be published without marking instructions.")
        if org_id is None and not version_row.marking_layout:
            raise domain.InvalidRubric(
                "Platform catalogue rubrics need an examiner marking layout before publish."
            )
    except Exception as exc:  # noqa: BLE001
        raise_mapped(exc, REFUSALS)
    await repository.set_version_status(session, org_id, version_row.id, status=status, at=now, by=actor_id)
    await repository.set_current_version(session, org_id, rubric_id, version_id=version_row.id)
    await session.refresh(version_row)
    return version_read(version_row)


async def archive_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    rubric_id: uuid.UUID,
    version: int,
    *,
    actor_id: uuid.UUID | None,
    now: datetime,
) -> RubricVersionRead:
    """Retire a published version from use. Refused unless it is published."""
    version_row = await _version(session, org_id, rubric_id, version)
    try:
        status = lifecycle.archive(
            lifecycle.VersionRef(number=version_row.version, status=lifecycle.Status(version_row.status))
        )
    except Exception as exc:  # noqa: BLE001
        raise_mapped(exc, REFUSALS)
    await repository.set_version_status(session, org_id, version_row.id, status=status, at=now, by=actor_id)
    await session.refresh(version_row)
    return version_read(version_row)


async def _own_rubric(session: AsyncSession, org_id: uuid.UUID | None, rubric_id: uuid.UUID) -> Rubric:
    """This owner's own rubric row, or the refusal if it does not belong to them."""
    rubric = await repository.rubric_by_id(session, org_id, rubric_id)
    if rubric is None:
        raise errors.RubricNotFound()
    return rubric


async def _version(
    session: AsyncSession, org_id: uuid.UUID | None, rubric_id: uuid.UUID, version: int
) -> RubricVersion:
    """This owner's own version by number, or the refusal if either is unknown."""
    await _own_rubric(session, org_id, rubric_id)
    version_row = await repository.version_by_number(session, org_id, rubric_id, version)
    if version_row is None:
        raise errors.RubricVersionNotFound()
    return version_row


# --- Mapping a rubric row onto the schema the routes return.


def validated(
    structure: dict[str, Any], pacing: dict[str, Any]
) -> tuple[domain.RubricStructure, dict[str, int]]:
    """Parse a structure and pacing together, mapping either's refusal to the same error."""
    try:
        return domain.parse_structure(structure), domain.validate_pacing(pacing)
    except domain.InvalidRubric as exc:
        raise errors.InvalidRubricError(str(exc)) from exc


def validate_marking_layout(marking_layout: dict[str, Any] | None) -> None:
    """An examiner marking layout, if given, must actually describe some sections."""
    if marking_layout is None:
        return
    if not isinstance(marking_layout, dict) or not marking_layout.get("sections"):
        raise errors.InvalidRubricError("A marking layout must include sections.")


def rubric_read(rubric: Rubric, versions: list[RubricVersion]) -> RubricRead:
    """Map a stored rubric and its versions onto what a route returns."""
    return RubricRead(
        id=rubric.id,
        owner_kind=rubric.owner_kind,
        org_id=rubric.org_id,
        title=rubric.title,
        current_version_id=rubric.current_version_id,
        versions=[version_read(version) for version in versions],
    )


def version_read(version: RubricVersion) -> RubricVersionRead:
    """Map a stored version onto what a route returns, deriving its result schema."""
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
        marking_layout=dict(version.marking_layout) if version.marking_layout else None,
        published_at=version.published_at,
    )
