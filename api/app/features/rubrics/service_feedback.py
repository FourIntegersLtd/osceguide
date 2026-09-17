"""Feedback template authoring: narrowing a rubric for one set of reviewers.

A feedback template says which of a rubric's domains its reviewers work
through. It used to name an *exam* and narrow "the platform marking schema",
which meant whichever of four shipped schemas that exam happened to bind — so
it could not be checked against anything, and an org could select a domain
that did not exist. It now names the rubric version it narrows, and the
selection is validated against that rubric's own domains.

Lives beside rubrics because it is a view of one. The lifecycle is the same
state machine as everything else versioned here.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import lifecycle
from app.core.errors import raise_mapped
from app.features.rubrics import domain, errors, service_marking
from app.features.rubrics import repository_feedback as repository
from app.features.rubrics.models import FeedbackTemplate, FeedbackTemplateVersion
from app.features.rubrics.schemas import FeedbackTemplateRead, FeedbackTemplateVersionRead
from app.features.rubrics.service import REFUSALS as _REFUSALS


async def create_feedback_template(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    title: str,
    rubric_version_id: uuid.UUID,
    field_selection: dict[str, Any],
) -> FeedbackTemplateRead:
    """A template and its first draft version, ready to edit or publish.

    The rubric must be published and readable by this owner: an org may narrow
    the platform's rubric or its own, and nobody may narrow a draft.
    """
    await _validated_selection(session, org_id, rubric_version_id, field_selection)
    template = await repository.create_feedback_template(
        session, org_id, rubric_version_id=rubric_version_id, title=title
    )
    version = await repository.add_feedback_template_version(
        session, org_id, template_id=template.id, version=1, field_selection=field_selection
    )
    return _template_read(template, [version])


async def list_feedback_templates(
    session: AsyncSession, org_id: uuid.UUID | None
) -> list[FeedbackTemplateRead]:
    out: list[FeedbackTemplateRead] = []
    for template in await repository.feedback_templates_for_org(session, org_id):
        versions = await repository.feedback_template_versions(session, org_id, template.id)
        out.append(_template_read(template, versions))
    return out


async def _validated_selection(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    rubric_version_id: uuid.UUID,
    field_selection: dict[str, Any],
) -> None:
    """Refuse a selection the rubric cannot satisfy.

    Nothing checked this before, because there was no rubric to check against:
    a template could name a domain no schema had, and the review built on it
    could never be completed.
    """
    version = await service_marking.published_version(session, org_id, rubric_version_id)
    try:
        domain.narrow_structure(domain.parse_structure(version.structure), field_selection)
    except domain.InvalidRubric as exc:
        raise errors.InvalidRubricError(str(exc)) from exc


async def add_feedback_template_version(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID
) -> FeedbackTemplateVersionRead:
    """Open a new draft, seeded from the latest published version."""
    await _require_template(session, org_id, template_id)
    existing = await repository.feedback_template_versions(session, org_id, template_id)
    refs = [lifecycle.VersionRef(number=v.version, status=lifecycle.Status(v.status)) for v in existing]
    seed = lifecycle.seed_version(refs)
    selection: dict[str, Any] = {}
    if seed is not None:
        selection = dict(next(v for v in existing if v.version == seed.number).field_selection)
    row = await repository.add_feedback_template_version(
        session,
        org_id,
        template_id=template_id,
        version=lifecycle.next_version_number(refs),
        field_selection=selection,
    )
    return _version_read(row)


async def edit_feedback_template_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    template_id: uuid.UUID,
    version: int,
    *,
    field_selection: dict[str, Any],
) -> FeedbackTemplateVersionRead:
    row = await _version(session, org_id, template_id, version)
    template = await _require_template(session, org_id, template_id)
    await _validated_selection(session, org_id, template.rubric_version_id, field_selection)
    try:
        lifecycle.ensure_editable(
            lifecycle.VersionRef(number=row.version, status=lifecycle.Status(row.status))
        )
    except lifecycle.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.set_feedback_template_version_selection(
        session, org_id, row.id, field_selection=field_selection
    )
    return _version_read(await _version(session, org_id, template_id, version))


async def publish_feedback_template(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    template_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None,
    now: datetime,
) -> FeedbackTemplateVersionRead:
    """Publish the newest version, which is then what a sitting may bind (S1).

    The newest, not "the draft": a template has at most one open draft, always
    its latest version, so naming it in the URL would add nothing but a way to
    get it wrong.
    """
    await _require_template(session, org_id, template_id)
    versions = await repository.feedback_template_versions(session, org_id, template_id)
    if not versions:
        raise errors.VersionNotFound()
    latest = max(versions, key=lambda v: v.version)
    try:
        status = lifecycle.publish(
            lifecycle.VersionRef(number=latest.version, status=lifecycle.Status(latest.status))
        )
    except lifecycle.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.set_feedback_template_version_status(
        session, org_id, latest.id, status=str(status), at=now, by=actor_id
    )
    return _version_read(await _version(session, org_id, template_id, latest.version))


async def reviewable_domains_for_version(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> set[str]:
    """Which domains a review against this template must score (R-1)."""
    row = await repository.feedback_template_version(session, org_id, version_id)
    if row is None:
        raise errors.TemplateVersionNotFound()
    return set(domain.reviewable_domains(row.field_selection))


async def rubric_binding_for(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> tuple[uuid.UUID, dict[str, Any] | None] | None:
    """The rubric this template narrows, and what it narrows it to.

    Returns None when the version cannot be read, so an attempt falls back to
    the exam's own rubric rather than failing the session outright.
    """
    row = await repository.feedback_template_version(session, org_id, version_id)
    if row is None:
        return None
    template = await repository.feedback_template_by_id(session, org_id, row.template_id)
    if template is None:
        return None
    return template.rubric_version_id, dict(row.field_selection or {})


async def _require_template(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID
) -> FeedbackTemplate:
    row = await repository.feedback_template_by_id(session, org_id, template_id)
    if row is None:
        raise errors.FeedbackTemplateNotFound()
    return row


async def _version(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID, version: int
) -> FeedbackTemplateVersion:
    await _require_template(session, org_id, template_id)
    for row in await repository.feedback_template_versions(session, org_id, template_id):
        if row.version == version:
            return row
    raise errors.VersionNotFound()


def _template_read(
    template: FeedbackTemplate, versions: list[FeedbackTemplateVersion]
) -> FeedbackTemplateRead:
    return FeedbackTemplateRead(
        id=template.id,
        title=template.title,
        owner_kind=template.owner_kind,
        rubric_version_id=template.rubric_version_id,
        versions=[_version_read(v) for v in versions],
    )


def _version_read(row: FeedbackTemplateVersion) -> FeedbackTemplateVersionRead:
    return FeedbackTemplateVersionRead(
        id=row.id,
        template_id=row.template_id,
        version=row.version,
        status=row.status,
        field_selection=dict(row.field_selection or {}),
        published_at=row.published_at,
    )


async def published_feedback_template(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> FeedbackTemplateVersion:
    """The feedback template version a sitting may bind (S1).

    Raises if it is missing, belongs to another org, or is still a draft. The
    NOT NULL foreign key on `sittings` made this look enforced, but a foreign
    key only says the row exists — a sitting could bind a rubric somebody was
    still editing, and candidates would be marked against it.
    """
    row = await repository.feedback_template_version(session, org_id, version_id)
    if row is None:
        raise errors.TemplateVersionNotFound()
    if row.status != "published":
        raise errors.FeedbackTemplateNotPublished("A sitting needs a published feedback template version.")
    return row


async def count_published_versions(session: AsyncSession, org_id: uuid.UUID | None) -> int:
    """How many published feedback templates an owner has; a sitting needs one."""
    return await repository.count_published_versions(session, org_id)
