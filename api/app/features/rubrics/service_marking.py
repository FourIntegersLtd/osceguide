"""Handing a rubric to whatever is about to mark with it.

`marking_snapshot` is the outward-facing one: it returns the rubric as the
engine wants it — a framework, its prompt, its clock — so the caller can freeze
that onto an attempt and mark it later without reading a row that may since
have changed. Re-marking an attempt a year from now then uses the wording it
was assessed against rather than whatever the rubric says today.

Split from `service.py` along the same line the slice is split on: that module
is about writing a rubric, this one is about using one.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import lifecycle
from app.features.rubrics import domain, errors, repository
from app.features.rubrics.models import RubricVersion


async def published_version(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> RubricVersion:
    """A published rubric version this owner may use, or a refusal saying why."""
    row = await repository.version_by_id(session, org_id, version_id)
    if row is None:
        raise errors.RubricVersionNotFound()
    if row.status != lifecycle.Status.PUBLISHED:
        raise errors.RubricVersionNotPublished()
    return row


async def published_platform_version(session: AsyncSession, version_id: uuid.UUID) -> RubricVersion:
    """What an exam may be marked with: published, and owned by the platform."""
    row = await repository.published_platform_version(session, version_id)
    if row is None:
        raise errors.RubricVersionNotFound("An exam must name a published rubric version the platform owns.")
    return row


async def marking_snapshot(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    rubric_version_id: uuid.UUID,
    field_selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The rubric as the engine needs it, ready to be frozen onto an attempt.

    Frozen rather than looked up at marking time so that re-marking an attempt
    a year later uses the wording it was assessed against, not whatever the
    rubric says now. `field_selection` narrows it to the domains a feedback
    template asks for.
    """
    version = await published_version(session, org_id, rubric_version_id)
    rubric = await repository.readable_rubric(session, org_id, version.rubric_id)
    structure = domain.narrow_structure(domain.parse_structure(version.structure), field_selection)
    return {
        "framework": domain.framework_payload(
            framework_id=str(version.id),
            label=rubric.title if rubric else "Rubric",
            version=str(version.version),
            structure=structure,
            system_prompt=version.system_prompt,
            override=version.result_schema_override,
        ),
        "system_prompt": version.system_prompt,
        "pacing": dict(version.pacing or {}),
    }


def reviewable_domains(field_selection: dict[str, Any] | None) -> set[str]:
    """Which domains a feedback template asks reviewers to score.

    Pure, but exposed on the service because it is the door other slices use:
    `reviews` needs to know what a complete review is, and `sittings` needs to
    know what it is binding.
    """
    return set(domain.reviewable_domains(field_selection))
