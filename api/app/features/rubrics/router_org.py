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
from app.features.rubrics import errors, schemas, service

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
async def list_org_rubrics(workspace: OrgReader, session: Session, page: Pager) -> Page[schemas.RubricRead]:
    """The organisation's own rubrics, and the platform's, which it may mark with."""
    items, next_cursor = await service.list_rubrics(
        session, workspace.org_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=items, next_cursor=next_cursor)


@router.get(
    "/orgs/{org_slug}/rubrics/{rubric_id}",
    response_model=schemas.RubricRead,
    responses=error_responses(Forbidden, *_NOT_FOUND),
)
async def read_org_rubric(rubric_id: uuid.UUID, workspace: OrgReader, session: Session) -> schemas.RubricRead:
    return await service.read_rubric(session, workspace.org_id, rubric_id)


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
        result_schema_override=body.result_schema_override,
    )


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
        result_schema_override=body.result_schema_override,
    )


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
