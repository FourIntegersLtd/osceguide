from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.tenancy import OrgAdmin, OrgReader
from app.features.catalog import errors, schemas, service

router = APIRouter(tags=["catalog"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/exams",
    response_model=Page[schemas.ExamRead],
    responses=error_responses(Unauthenticated),
)
async def list_exams(principal: CurrentPrincipal, session: Session) -> Page[schemas.ExamRead]:
    """The four published exams. Closed set, so no cursor is ever returned."""
    return Page(items=await service.list_exams(session), next_cursor=None)


@router.get(
    "/orgs/{org_slug}/programmes",
    response_model=Page[schemas.ProgrammeRead],
    responses=error_responses(Forbidden),
)
async def list_programmes(
    workspace: OrgReader, session: Session, page: Annotated[CursorParams, Depends()]
) -> Page[schemas.ProgrammeRead]:
    items, next_cursor = await service.list_programmes(
        session, workspace.org_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=items, next_cursor=next_cursor)


@router.post(
    "/orgs/{org_slug}/programmes",
    response_model=schemas.ProgrammeRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.ProgrammeExists, errors.UnknownExamError),
)
async def add_programme(
    body: schemas.CreateProgramme, workspace: OrgAdmin, session: Session
) -> schemas.ProgrammeRead:
    return await service.add_programme(session, workspace.org_id, exam_code=body.exam_code)


@router.patch(
    "/orgs/{org_slug}/programmes/{programme_id}",
    response_model=schemas.ProgrammeRead,
    responses=error_responses(Forbidden, errors.ProgrammeNotFound),
)
async def update_programme(
    programme_id: uuid.UUID,
    body: schemas.UpdateProgramme,
    workspace: OrgAdmin,
    session: Session,
) -> schemas.ProgrammeRead:
    return await service.set_programme_status(session, workspace.org_id, programme_id, status=body.status)
