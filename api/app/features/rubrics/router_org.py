"""Rubric authoring for one organisation.

The platform half is in `router.py`; see its docstring for why there are two.
An org sees the platform's rubrics as well as its own when reading, and may
write only its own.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.tenancy import OrgAdmin, OrgReader
from app.features.rubrics import errors, schemas, service, service_authoring

router = APIRouter(tags=["rubrics"])

Session = Annotated[AsyncSession, Depends(get_session)]
Pager = Annotated[CursorParams, Depends()]

_NOT_FOUND = (errors.RubricNotFound, errors.RubricVersionNotFound)
_LIFECYCLE = (errors.NotEditableError, errors.AlreadyPublishedError, errors.NotArchivableError)


@router.get(
    "/orgs/{org_slug}/rubrics",
    response_model=Page[schemas.RubricRead],
    responses=error_responses(Forbidden),
)
async def list_org_rubrics(
    workspace: OrgReader,
    session: Session,
    page: Pager,
    search: str | None = None,
    exam_code: str | None = None,
) -> Page[schemas.RubricRead]:
    """The organisation's own rubrics, and the platform's, which it may mark with.

    `search` matches a rubric's title; `exam_code` narrows to rubrics already
    bound to that exam (the platform-web author screen used to do this join
    client-side).
    """
    rubrics, next_cursor = await service.list_rubrics(
        session, workspace.org_id, limit=page.limit, cursor=page.cursor, search=search, exam_code=exam_code
    )
    return Page(items=rubrics, next_cursor=next_cursor)


# What a new rubric may start from: blank, the platform's published rubrics, then the org's own.
# Registered before `/rubrics/{rubric_id}`, which would otherwise read "starting-points" as an id.
@router.get(
    "/orgs/{org_slug}/rubrics/starting-points",
    response_model=schemas.RubricStartingPointsRead,
    responses=error_responses(Forbidden),
)
async def org_rubric_starting_points(
    workspace: OrgAdmin, session: Session, search: str | None = None
) -> schemas.RubricStartingPointsRead:
    return await service_authoring.starting_points(session, workspace.org_id, search=search)


# Attempts this organisation's admin may trial-mark against (rubrics plan §8, R-6): paginated, searchable.
# Registered before `/rubrics/{rubric_id}`, which would otherwise read "trial-candidates" as an id.
@router.get(
    "/orgs/{org_slug}/rubrics/trial-candidates",
    response_model=Page[schemas.TrialCandidateRead],
    responses=error_responses(Forbidden),
)
async def list_org_trial_candidates(
    workspace: OrgAdmin, session: Session, page: Pager, search: str | None = None
) -> Page[schemas.TrialCandidateRead]:
    return await service.trial_candidates(
        session, workspace.org_id, limit=page.limit, cursor=page.cursor, search=search
    )


# Read one of an organisation's rubrics.
@router.get(
    "/orgs/{org_slug}/rubrics/{rubric_id}",
    response_model=schemas.RubricRead,
    responses=error_responses(Forbidden, *_NOT_FOUND),
)
async def read_org_rubric(rubric_id: uuid.UUID, workspace: OrgReader, session: Session) -> schemas.RubricRead:
    return await service.read_rubric(session, workspace.org_id, rubric_id)


@router.patch(
    "/orgs/{org_slug}/rubrics/{rubric_id}",
    response_model=schemas.RubricRead,
    responses=error_responses(Forbidden, *_NOT_FOUND),
)
async def rename_org_rubric(
    rubric_id: uuid.UUID, body: schemas.RenameRubric, workspace: OrgAdmin, session: Session
) -> schemas.RubricRead:
    """Change this organisation's rubric title. Every version keeps it; nothing about marking changes."""
    return await service.rename_rubric(session, workspace.org_id, rubric_id, title=body.title)


# A new rubric owned by this organisation, with its first draft version.
@router.post(
    "/orgs/{org_slug}/rubrics",
    response_model=schemas.RubricRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.InvalidRubricError),
)
async def create_org_rubric(
    body: schemas.CreateRubric, workspace: OrgAdmin, session: Session
) -> schemas.RubricRead:
    return await service.create_rubric(
        session,
        workspace.org_id,
        title=body.title,
        structure=body.structure,
        system_prompt=body.system_prompt,
        pacing=body.pacing,
        marking_layout=body.marking_layout,
    )


# Add a new version to one of an organisation's rubrics.
@router.post(
    "/orgs/{org_slug}/rubrics/{rubric_id}/versions",
    response_model=schemas.RubricVersionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, *_NOT_FOUND),
)
async def add_org_version(
    rubric_id: uuid.UUID, workspace: OrgAdmin, session: Session
) -> schemas.RubricVersionRead:
    return await service.add_version(session, workspace.org_id, rubric_id)


# Rewrite this organisation's own draft version. Refused once it is published.
@router.patch(
    "/orgs/{org_slug}/rubrics/{rubric_id}/versions/{version}",
    response_model=schemas.RubricVersionRead,
    responses=error_responses(Forbidden, *_NOT_FOUND, *_LIFECYCLE, errors.InvalidRubricError),
)
async def edit_org_version(
    rubric_id: uuid.UUID,
    version: int,
    body: schemas.EditRubricVersion,
    workspace: OrgAdmin,
    session: Session,
) -> schemas.RubricVersionRead:
    return await service.edit_version(
        session,
        workspace.org_id,
        rubric_id,
        version,
        structure=body.structure,
        system_prompt=body.system_prompt,
        pacing=body.pacing,
        marking_layout=body.marking_layout,
    )


# Make this version the one new attempts against this organisation's exams are marked with.
@router.post(
    "/orgs/{org_slug}/rubrics/{rubric_id}/versions/{version}/publish",
    response_model=schemas.RubricVersionRead,
    responses=error_responses(Forbidden, *_NOT_FOUND, *_LIFECYCLE, errors.InvalidRubricError),
)
async def publish_org_version(
    rubric_id: uuid.UUID, version: int, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.RubricVersionRead:
    return await service.publish_version(
        session,
        workspace.org_id,
        rubric_id,
        version,
        actor_id=workspace.principal.user_id,
        now=clock.now(),
    )


# Retire this organisation's own version from use. Only a published version can be archived.
@router.post(
    "/orgs/{org_slug}/rubrics/{rubric_id}/versions/{version}/archive",
    response_model=schemas.RubricVersionRead,
    responses=error_responses(Forbidden, *_NOT_FOUND, *_LIFECYCLE),
)
async def archive_org_version(
    rubric_id: uuid.UUID, version: int, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.RubricVersionRead:
    return await service.archive_version(
        session,
        workspace.org_id,
        rubric_id,
        version,
        actor_id=workspace.principal.user_id,
        now=clock.now(),
    )


# Check a draft structure and show what it comes to: schemas, resolved display, a sample result.
# Answers 200 with `valid: false` and every problem while the draft cannot be published.
@router.post(
    "/orgs/{org_slug}/rubrics/preview",
    response_model=schemas.RubricPreviewRead,
    responses=error_responses(Forbidden),
)
async def preview_org_rubric(body: schemas.RubricDraft, workspace: OrgAdmin) -> schemas.RubricPreviewRead:
    return service_authoring.preview(body.structure)


# A new rubric of this organisation's: blank, or a draft copy of a published platform or own rubric.
@router.post(
    "/orgs/{org_slug}/rubrics/copy",
    response_model=schemas.RubricRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, *_NOT_FOUND, errors.RubricVersionNotPublished),
)
async def copy_org_rubric(
    body: schemas.CopyRubric, workspace: OrgAdmin, session: Session
) -> schemas.RubricRead:
    return await service_authoring.copy_rubric(
        session,
        workspace.org_id,
        source_rubric_id=body.source_rubric_id,
        source_version=body.source_version,
        title=body.title,
    )


# Suggested instructions for every place in a draft structure: the copied rubric's own, else generic.
@router.post(
    "/orgs/{org_slug}/rubrics/draft-instructions",
    response_model=schemas.DraftInstructionsRead,
    responses=error_responses(Forbidden, errors.InvalidRubricError),
)
async def draft_org_rubric_instructions(
    body: schemas.RubricDraft, workspace: OrgAdmin, session: Session
) -> schemas.DraftInstructionsRead:
    return await service_authoring.draft_instructions(session, workspace.org_id, body.structure)
