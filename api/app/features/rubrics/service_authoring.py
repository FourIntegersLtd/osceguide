"""What the rubric builder needs beyond saving a version (plan §8, Stage 4).

Checking and previewing a draft structure, starting a new rubric from a blank
one or a copy of a published one, the list of what one may start from, and
draft instructions for every place a structure carries them.

The same functions serve both doors (`router.py` for the platform, with
`org_id=None`, and `router_org.py`), so permissions stay what they were:
whoever may author a rubric there may use these.
"""

from __future__ import annotations

import json
import uuid
from functools import cache
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import lifecycle
from app.features.rubrics import authoring, domain, errors, repository, service_marking
from app.features.rubrics.models import RubricVersion
from app.features.rubrics.schemas import (
    DraftInstructionRead,
    DraftInstructionsRead,
    RubricPreviewRead,
    RubricRead,
    RubricStartingPointRead,
    RubricStartingPointsRead,
)
from app.features.rubrics.service import domain_titles, parsed_or_problems, rubric_read

_GENERIC_PROFILE = Path(__file__).parent / "profiles" / "_generic.json"
_BLANK_TITLE = "Untitled rubric"
_TITLE_LIMIT = 200


def preview(structure: dict[str, Any]) -> RubricPreviewRead:
    """Everything a draft structure comes to, or every reason it cannot be published yet.

    Also the builder's validation: `valid` and `problems` are the same check
    publishing makes of the structure. Never refused, so it answers mid-edit.
    """
    parsed, problems = parsed_or_problems(structure)
    if parsed is None:
        return RubricPreviewRead(valid=False, problems=problems)
    display = domain.resolved_display(parsed)
    sample = authoring.sample_result(parsed)
    scoring_rubric = service_marking.ScoringRubric(
        structure=parsed, raw_structure=domain.upgrade_structure(structure), display=display, version_id=None
    )
    return RubricPreviewRead(
        valid=True,
        structure=scoring_rubric.raw_structure,
        result_schema=domain.derive_result_schema(parsed),
        display_schema=domain.derive_display_schema(parsed),
        display=display,
        rating=service_marking.rating_read(parsed),
        sample_result=sample,
        sample_totals=service_marking.totals_read(scoring_rubric, sample),
    )


async def copy_rubric(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    source_rubric_id: uuid.UUID | None,
    source_version: int | None,
    title: str | None,
) -> RubricRead:
    """A new rubric of this owner's, its first version a draft: blank, or a copy of a published version.

    The source must be one this owner may read (its own or the platform's) and
    the version published: a draft is still somebody else's work in progress.
    Its structure (as version 2, remembering where it came from), marking
    instructions, pacing and marking layout are all copied.
    """
    if source_rubric_id is None:
        rubric = await repository.create_rubric(session, org_id, title=title or _BLANK_TITLE)
        first = await repository.add_version(
            session,
            org_id,
            rubric_id=rubric.id,
            version=1,
            structure=authoring.blank_scheme(),
            system_prompt=authoring.BLANK_SYSTEM_PROMPT,
            pacing=dict(authoring.BLANK_PACING),
        )
        return rubric_read(rubric, [first])

    source = await repository.readable_rubric(session, org_id, source_rubric_id)
    if source is None:
        raise errors.RubricNotFound()
    source_row = await _readable_version(
        session, org_id, source_rubric_id, source_version, source.current_version_id
    )
    if source_row.status != lifecycle.Status.PUBLISHED:
        raise errors.RubricVersionNotPublished("Only a published rubric version can be copied.")
    structure = authoring.with_origin(
        domain.authoring_form(source_row.structure),
        rubric_id=str(source.id),
        version=source_row.version,
        title=source.title,
    )
    copy_title = title or f"{source.title} (copy)"[:_TITLE_LIMIT]
    rubric = await repository.create_rubric(session, org_id, title=copy_title)
    first = await repository.add_version(
        session,
        org_id,
        rubric_id=rubric.id,
        version=1,
        structure=structure,
        system_prompt=source_row.system_prompt,
        pacing=dict(source_row.pacing or {}),
        marking_layout=dict(source_row.marking_layout) if source_row.marking_layout else None,
    )
    return rubric_read(rubric, [first])


async def _readable_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    rubric_id: uuid.UUID,
    version: int | None,
    current_version_id: uuid.UUID | None,
) -> RubricVersion:
    """A version of a readable rubric by number, or its current one when no number is given."""
    for version_row in await repository.versions_for_rubric(session, org_id, rubric_id):
        if (version is None and version_row.id == current_version_id) or version_row.version == version:
            return version_row
    if version is None:
        raise errors.RubricVersionNotPublished("This rubric has no published version to copy.")
    raise errors.RubricVersionNotFound()


async def starting_points(
    session: AsyncSession, org_id: uuid.UUID | None, *, search: str | None = None
) -> RubricStartingPointsRead:
    """The builder's "Start from" chooser: blank, then the platform's rubrics, then the owner's own."""
    blank = authoring.blank_structure()
    items = [
        RubricStartingPointRead(
            kind="blank",
            title="Blank rubric",
            rating_kind=blank["rating"]["kind"],
            domains=[title for _, title in domain_titles(blank)],
            competency_count=1,
        )
    ]
    for rubric, version_row in await repository.published_current_versions(session, org_id, search=search):
        parsed, _ = parsed_or_problems(version_row.structure)
        if parsed is None:
            # Published before today's rules; it cannot be copied into anything publishable.
            continue
        items.append(
            RubricStartingPointRead(
                kind="platform" if rubric.org_id is None else "own",
                rubric_id=rubric.id,
                version=version_row.version,
                title=rubric.title,
                rating_kind=parsed.rating.kind,
                domains=[title for _, title in domain_titles(version_row.structure)],
                competency_count=len(parsed.competencies),
            )
        )
    return RubricStartingPointsRead(items=items)


async def draft_instructions(
    session: AsyncSession, org_id: uuid.UUID | None, structure: dict[str, Any]
) -> DraftInstructionsRead:
    """Suggested instructions for every place in a draft structure that carries them.

    A structure copied from another rubric is given that rubric's own wording
    wherever an id still matches; everything else gets the generic wording for
    its role (`profiles/_generic.json`). Nothing is saved: the builder decides
    what to keep.
    """
    try:
        upgraded = domain.upgrade_structure(structure)
    except domain.InvalidRubric as exc:
        raise errors.InvalidRubricError(str(exc), details={"errors": domain.validation_errors(exc)}) from exc
    source_profile = await _origin_profile(session, org_id, upgraded)
    return DraftInstructionsRead(
        items=[
            DraftInstructionRead(
                path=slot.path,
                key=slot.key,
                kind=slot.kind,
                role=slot.role,
                text=text,
                source=source,
                has_instructions=bool(slot.current.strip()),
            )
            for slot, text, source in authoring.draft_instructions(
                upgraded, source_profile, _generic_profile()
            )
        ]
    )


async def _origin_profile(
    session: AsyncSession, org_id: uuid.UUID | None, structure: dict[str, Any]
) -> dict[str, str]:
    """The wording of the rubric a structure was copied from, when this owner may still read it."""
    origin = authoring.origin_of(structure)
    if origin is None:
        return {}
    rubric_id_text, version_number = origin
    try:
        rubric_id = uuid.UUID(rubric_id_text)
    except ValueError:
        return {}
    for version_row in await repository.versions_for_rubric(session, org_id, rubric_id):
        if version_row.version == version_number:
            try:
                return authoring.profile_of(domain.upgrade_structure(version_row.structure))
            except domain.InvalidRubric:
                return {}
    return {}


@cache
def _generic_profile() -> dict[str, str]:
    """The wording used for any role or kind the source rubric says nothing about."""
    loaded: dict[str, str] = json.loads(_GENERIC_PROFILE.read_text())
    return loaded
