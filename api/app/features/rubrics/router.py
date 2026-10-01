"""Rubric authoring for the platform: the library every organisation may mark with.

The org-facing half of the same service is in `router_org.py`. They differ only
in who is allowed in and what they own — `org_id=None` here, the workspace's org
there — which is the whole of "irrespective of whether it is an exam or an
institution": the same tables, the same lifecycle, two doors.

A platform admin is deliberately not an org admin (`OrgAdmin` sets
`allow_platform_admin=False`), so neither can author the other's rubrics.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.tenancy import PlatformAdmin
from app.features.rubrics import errors, schemas, service, service_authoring

router = APIRouter(tags=["rubrics"])

Session = Annotated[AsyncSession, Depends(get_session)]
Pager = Annotated[CursorParams, Depends()]

_NOT_FOUND = (errors.RubricNotFound, errors.RubricVersionNotFound)
_LIFECYCLE = (errors.NotEditableError, errors.AlreadyPublishedError, errors.NotArchivableError)


@router.post(
    "/platform/rubrics",
    response_model=schemas.RubricRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Unauthenticated, Forbidden, errors.InvalidRubricError),
)
async def create_platform_rubric(
    body: schemas.CreateRubric, admin: PlatformAdmin, session: Session
) -> schemas.RubricRead:
    """The platform's own rubric: what its published exams are marked against."""
    return await service.create_rubric(
        session,
        None,
        title=body.title,
        structure=body.structure,
        system_prompt=body.system_prompt,
        pacing=body.pacing,
        marking_layout=body.marking_layout,
    )


# The platform's own rubric library, newest first.
@router.get(
    "/platform/rubrics",
    response_model=Page[schemas.RubricRead],
    responses=error_responses(Unauthenticated, Forbidden),
)
async def list_platform_rubrics(
    admin: PlatformAdmin,
    session: Session,
    page: Pager,
    search: str | None = None,
    exam_code: str | None = None,
) -> Page[schemas.RubricRead]:
    """`search` matches a rubric's title; `exam_code` narrows to rubrics already
    bound to that exam."""
    rubrics, next_cursor = await service.list_rubrics(
        session, None, limit=page.limit, cursor=page.cursor, search=search, exam_code=exam_code
    )
    return Page(items=rubrics, next_cursor=next_cursor)


# What a new platform rubric may start from: blank, or one of the platform's published rubrics.
# Registered before `/rubrics/{rubric_id}`, which would otherwise read "starting-points" as an id.
@router.get(
    "/platform/rubrics/starting-points",
    response_model=schemas.RubricStartingPointsRead,
    responses=error_responses(Unauthenticated, Forbidden),
)
async def platform_rubric_starting_points(
    admin: PlatformAdmin, session: Session, search: str | None = None
) -> schemas.RubricStartingPointsRead:
    return await service_authoring.starting_points(session, None, search=search)


# Attempts a platform admin may trial-mark against: the platform's own, outside any organisation.
# Registered before `/rubrics/{rubric_id}`, which would otherwise read "trial-candidates" as an id.
@router.get(
    "/platform/rubrics/trial-candidates",
    response_model=Page[schemas.TrialCandidateRead],
    responses=error_responses(Unauthenticated, Forbidden),
)
async def list_platform_trial_candidates(
    admin: PlatformAdmin, session: Session, page: Pager, search: str | None = None
) -> Page[schemas.TrialCandidateRead]:
    return await service.trial_candidates(session, None, limit=page.limit, cursor=page.cursor, search=search)


# Read one platform rubric.
@router.get(
    "/platform/rubrics/{rubric_id}",
    response_model=schemas.RubricRead,
    responses=error_responses(Unauthenticated, Forbidden, *_NOT_FOUND),
)
async def read_platform_rubric(
    rubric_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.RubricRead:
    return await service.read_rubric(session, None, rubric_id)


@router.patch(
    "/platform/rubrics/{rubric_id}",
    response_model=schemas.RubricRead,
    responses=error_responses(Unauthenticated, Forbidden, *_NOT_FOUND),
)
async def rename_platform_rubric(
    rubric_id: uuid.UUID, body: schemas.RenameRubric, admin: PlatformAdmin, session: Session
) -> schemas.RubricRead:
    """Change this platform rubric's title. Every version keeps it; nothing about marking changes."""
    return await service.rename_rubric(session, None, rubric_id, title=body.title)


# Add a new version to a platform rubric.
@router.post(
    "/platform/rubrics/{rubric_id}/versions",
    response_model=schemas.RubricVersionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Unauthenticated, Forbidden, *_NOT_FOUND),
)
async def add_platform_version(
    rubric_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.RubricVersionRead:
    return await service.add_version(session, None, rubric_id)


# Rewrite a draft platform version's body. Refused once it is published.
@router.patch(
    "/platform/rubrics/{rubric_id}/versions/{version}",
    response_model=schemas.RubricVersionRead,
    responses=error_responses(
        Unauthenticated, Forbidden, *_NOT_FOUND, *_LIFECYCLE, errors.InvalidRubricError
    ),
)
async def edit_platform_version(
    rubric_id: uuid.UUID,
    version: int,
    body: schemas.EditRubricVersion,
    admin: PlatformAdmin,
    session: Session,
) -> schemas.RubricVersionRead:
    return await service.edit_version(
        session,
        None,
        rubric_id,
        version,
        structure=body.structure,
        system_prompt=body.system_prompt,
        pacing=body.pacing,
        marking_layout=body.marking_layout,
    )


# Make this version the one new attempts against the platform catalogue are marked with.
@router.post(
    "/platform/rubrics/{rubric_id}/versions/{version}/publish",
    response_model=schemas.RubricVersionRead,
    responses=error_responses(
        Unauthenticated, Forbidden, *_NOT_FOUND, *_LIFECYCLE, errors.InvalidRubricError
    ),
)
async def publish_platform_version(
    rubric_id: uuid.UUID, version: int, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.RubricVersionRead:
    return await service.publish_version(
        session, None, rubric_id, version, actor_id=admin.user_id, now=clock.now()
    )


# Retire this platform version from use. Only a published version can be archived.
@router.post(
    "/platform/rubrics/{rubric_id}/versions/{version}/archive",
    response_model=schemas.RubricVersionRead,
    responses=error_responses(Unauthenticated, Forbidden, *_NOT_FOUND, *_LIFECYCLE),
)
async def archive_platform_version(
    rubric_id: uuid.UUID, version: int, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.RubricVersionRead:
    return await service.archive_version(
        session, None, rubric_id, version, actor_id=admin.user_id, now=clock.now()
    )


# Check a draft structure and show what it comes to: schemas, resolved display, a sample result.
# Answers 200 with `valid: false` and every problem while the draft cannot be published.
@router.post(
    "/platform/rubrics/preview",
    response_model=schemas.RubricPreviewRead,
    responses=error_responses(Unauthenticated, Forbidden),
)
async def preview_platform_rubric(
    body: schemas.RubricDraft, admin: PlatformAdmin
) -> schemas.RubricPreviewRead:
    return service_authoring.preview(body.structure)


# A new platform rubric: blank, or a draft copy of a published platform rubric.
@router.post(
    "/platform/rubrics/copy",
    response_model=schemas.RubricRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Unauthenticated, Forbidden, *_NOT_FOUND, errors.RubricVersionNotPublished),
)
async def copy_platform_rubric(
    body: schemas.CopyRubric, admin: PlatformAdmin, session: Session
) -> schemas.RubricRead:
    return await service_authoring.copy_rubric(
        session,
        None,
        source_rubric_id=body.source_rubric_id,
        source_version=body.source_version,
        title=body.title,
    )


# Suggested instructions for every place in a draft structure: the copied rubric's own, else generic.
@router.post(
    "/platform/rubrics/draft-instructions",
    response_model=schemas.DraftInstructionsRead,
    responses=error_responses(Unauthenticated, Forbidden, errors.InvalidRubricError),
)
async def draft_platform_rubric_instructions(
    body: schemas.RubricDraft, admin: PlatformAdmin, session: Session
) -> schemas.DraftInstructionsRead:
    return await service_authoring.draft_instructions(session, None, body.structure)
