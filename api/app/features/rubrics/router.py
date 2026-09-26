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
from app.features.rubrics import errors, schemas, service

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
        result_schema_override=body.result_schema_override,
        marking_layout=body.marking_layout,
    )


# The platform's own rubric library, newest first.
@router.get(
    "/platform/rubrics",
    response_model=Page[schemas.RubricRead],
    responses=error_responses(Unauthenticated, Forbidden),
)
async def list_platform_rubrics(
    admin: PlatformAdmin, session: Session, page: Pager
) -> Page[schemas.RubricRead]:
    rubrics, next_cursor = await service.list_rubrics(session, None, limit=page.limit, cursor=page.cursor)
    return Page(items=rubrics, next_cursor=next_cursor)


@router.get(
    "/platform/rubrics/{rubric_id}",
    response_model=schemas.RubricRead,
    responses=error_responses(Unauthenticated, Forbidden, *_NOT_FOUND),
)
async def read_platform_rubric(
    rubric_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.RubricRead:
    return await service.read_rubric(session, None, rubric_id)


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
        result_schema_override=body.result_schema_override,
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
