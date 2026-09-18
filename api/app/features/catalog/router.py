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
from app.features.catalog import errors, schemas, service_authoring, service_programmes

router = APIRouter(tags=["catalog"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/exams",
    response_model=Page[schemas.ExamRead],
    responses=error_responses(Unauthenticated),
)
async def list_exams(principal: CurrentPrincipal, session: Session) -> Page[schemas.ExamRead]:
    """The exams the platform offers. Small set, so no cursor is ever returned.

    The consumer catalogue: platform exams only. An institution's own exams are
    not here and never are — they are that institution's, not ours to publish.
    See `/orgs/{org_slug}/exams` for those.

    A platform admin sees the platform's drafts, because they are the person
    writing them, and nobody else's.
    """
    items = await service_authoring.list_exams(session, include_unpublished=principal.is_platform_admin)
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
    """A new platform exam, as a draft — the consumer catalogue.

    The table starts empty and stays that way until somebody writes one. There
    is no seed: four exams used to be inserted by a migration and mirrored by a
    tuple in this slice, and a fifth needed both changed and shipped.
    """
    return await service_authoring.create_exam(
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
    return await service_authoring.update_exam(session, exam_id, **body.model_dump(exclude_unset=True))


@router.post(
    "/platform/exams/{exam_id}/publish",
    response_model=schemas.ExamRead,
    responses=error_responses(Unauthenticated, Forbidden, errors.UnknownExamError, errors.ExamNotPublishable),
)
async def publish_exam(exam_id: uuid.UUID, admin: PlatformAdmin, session: Session) -> schemas.ExamRead:
    """Offer the exam. Refused until it names the rubric it is marked against."""
    return await service_authoring.publish_exam(session, exam_id)


@router.post(
    "/platform/exams/{exam_id}/retire",
    response_model=schemas.ExamRead,
    responses=error_responses(Unauthenticated, Forbidden, errors.UnknownExamError, errors.ExamNotPublishable),
)
async def retire_exam(exam_id: uuid.UUID, admin: PlatformAdmin, session: Session) -> schemas.ExamRead:
    """Stop offering it. Past attempts keep working; nothing new may name it."""
    return await service_authoring.retire_exam(session, exam_id)


@router.get(
    "/orgs/{org_slug}/exams",
    response_model=Page[schemas.ExamRead],
    responses=error_responses(Forbidden),
)
async def list_org_exams(
    workspace: OrgReader, session: Session, drafts: bool = False
) -> Page[schemas.ExamRead]:
    """This institution's own exams, plus the platform catalogue.

    `drafts=true` narrows to the institution's own rows, published or not: its
    drafts are its own business. It never widens the listing to the platform's
    drafts, which it cannot see at all.
    """
    items = await service_authoring.list_exams(session, org_id=workspace.org_id, include_unpublished=drafts)
    return Page(items=items, next_cursor=None)


@router.post(
    "/orgs/{org_slug}/exams",
    response_model=schemas.ExamRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        Forbidden,
        errors.ExamCodeTaken,
        errors.InvalidExamCodeError,
        errors.RubricVersionNotFound,
    ),
)
async def create_org_exam(
    body: schemas.CreateExam, workspace: OrgAdmin, session: Session
) -> schemas.ExamRead:
    """An institution's own exam, as a draft.

    Written without asking the platform and without picking from a list: an
    institution defines the exams it assesses against. The code is unique
    within this organisation only, so two schools may both have a `finals`.
    """
    return await service_authoring.create_exam(
        session,
        workspace.org_id,
        code=body.code,
        name=body.name,
        default_reading_seconds=body.default_reading_seconds,
        default_simulation_seconds=body.default_simulation_seconds,
        station_attempt_limit=body.station_attempt_limit,
        rubric_version_id=body.rubric_version_id,
    )


@router.patch(
    "/orgs/{org_slug}/exams/{exam_id}",
    response_model=schemas.ExamRead,
    responses=error_responses(Forbidden, errors.UnknownExamError, errors.RubricVersionNotFound),
)
async def update_org_exam(
    exam_id: uuid.UUID, body: schemas.UpdateExam, workspace: OrgAdmin, session: Session
) -> schemas.ExamRead:
    """Only this institution's own exams. A platform exam answers `unknown_exam`."""
    return await service_authoring.update_exam(
        session, exam_id, workspace.org_id, **body.model_dump(exclude_unset=True)
    )


@router.post(
    "/orgs/{org_slug}/exams/{exam_id}/publish",
    response_model=schemas.ExamRead,
    responses=error_responses(Forbidden, errors.UnknownExamError, errors.ExamNotPublishable),
)
async def publish_org_exam(exam_id: uuid.UUID, workspace: OrgAdmin, session: Session) -> schemas.ExamRead:
    """The institution's own call, on its own schedule. Refused without a rubric."""
    return await service_authoring.publish_exam(session, exam_id, workspace.org_id)


@router.post(
    "/orgs/{org_slug}/exams/{exam_id}/retire",
    response_model=schemas.ExamRead,
    responses=error_responses(Forbidden, errors.UnknownExamError, errors.ExamNotPublishable),
)
async def retire_org_exam(exam_id: uuid.UUID, workspace: OrgAdmin, session: Session) -> schemas.ExamRead:
    """Stop running it. Past sittings and their results are untouched."""
    return await service_authoring.retire_exam(session, exam_id, workspace.org_id)


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
    """Group this institution's sittings under one exam.

    The exam may be the institution's own or one the platform published; the
    code is resolved in the institution's scope, so its own wins a clash.
    """
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
