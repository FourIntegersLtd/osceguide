from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.tenancy import OrgAdmin, OrgReader, PlatformAdmin
from app.features.catalog import errors, schemas, service, service_programmes

router = APIRouter(tags=["catalog"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/exams",
    response_model=Page[schemas.ExamRead],
    responses=error_responses(Unauthenticated),
)
async def list_exams(principal: CurrentPrincipal, session: Session) -> Page[schemas.ExamRead]:
    """The exams the platform offers. Small set, so no cursor is ever returned.

    A platform admin also sees drafts, because they are the person writing them.
    """
    items = await service.list_exams(session, include_unpublished=principal.is_platform_admin)
    return Page(items=items, next_cursor=None)


@router.post(
    "/platform/exams",
    response_model=schemas.ExamRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        Unauthenticated,
        Forbidden,
        errors.ExamCodeTaken,
        errors.InvalidExamCodeError,
        errors.RubricVersionNotFound,
    ),
)
async def create_exam(body: schemas.CreateExam, admin: PlatformAdmin, session: Session) -> schemas.ExamRead:
    """A new exam, as a draft.

    The table starts empty and stays that way until somebody writes one. There
    is no seed: four exams used to be inserted by a migration and mirrored by a
    tuple in this slice, and a fifth needed both changed and shipped.
    """
    return await service.create_exam(
        session,
        code=body.code,
        name=body.name,
        default_reading_seconds=body.default_reading_seconds,
        default_simulation_seconds=body.default_simulation_seconds,
        station_attempt_limit=body.station_attempt_limit,
        rubric_version_id=body.rubric_version_id,
        partner_pilot=body.partner_pilot,
    )


@router.patch(
    "/platform/exams/{exam_id}",
    response_model=schemas.ExamRead,
    responses=error_responses(
        Unauthenticated, Forbidden, errors.UnknownExamError, errors.RubricVersionNotFound
    ),
)
async def update_exam(
    exam_id: uuid.UUID, body: schemas.UpdateExam, admin: PlatformAdmin, session: Session
) -> schemas.ExamRead:
    return await service.update_exam(session, exam_id, **body.model_dump(exclude_unset=True))


@router.post(
    "/platform/exams/{exam_id}/publish",
    response_model=schemas.ExamRead,
    responses=error_responses(Unauthenticated, Forbidden, errors.UnknownExamError, errors.ExamNotPublishable),
)
async def publish_exam(exam_id: uuid.UUID, admin: PlatformAdmin, session: Session) -> schemas.ExamRead:
    """Offer the exam. Refused until it names the rubric it is marked against."""
    return await service.publish_exam(session, exam_id)


@router.post(
    "/platform/exams/{exam_id}/retire",
    response_model=schemas.ExamRead,
    responses=error_responses(Unauthenticated, Forbidden, errors.UnknownExamError, errors.ExamNotPublishable),
)
async def retire_exam(exam_id: uuid.UUID, admin: PlatformAdmin, session: Session) -> schemas.ExamRead:
    """Stop offering it. Past attempts keep working; nothing new may name it."""
    return await service.retire_exam(session, exam_id)


@router.get(
    "/orgs/{org_slug}/programmes",
    response_model=Page[schemas.ProgrammeRead],
    responses=error_responses(Forbidden),
)
async def list_programmes(
    workspace: OrgReader, session: Session, page: Annotated[CursorParams, Depends()]
) -> Page[schemas.ProgrammeRead]:
    items, next_cursor = await service_programmes.list_programmes(
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
    return await service_programmes.add_programme(session, workspace.org_id, exam_code=body.exam_code)


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
    return await service_programmes.set_programme_status(
        session, workspace.org_id, programme_id, status=body.status
    )
