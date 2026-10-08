"""HTTP routes for browsing, authoring and publishing exams, and for grouping
them into an institution's programmes. Each hands straight to a `service*` module."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.tenancy import OrgAdmin, OrgStaff, PlatformAdmin
from app.features.catalog import errors, schemas, service_authoring, service_import, service_programmes

router = APIRouter(tags=["catalog"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/exams",
    response_model=Page[schemas.ExamRead],
    responses=error_responses(Unauthenticated),
)
async def list_exams(principal: CurrentPrincipal, session: Session) -> Page[schemas.ExamRead]:
    """The exams the platform offers. Small set, so no cursor is ever returned.

    The consumer catalogue: platform exams only. See `/orgs/{org_slug}/exams`
    for an institution's own. A platform admin also sees the platform's drafts.
    """
    exams = await service_authoring.list_exams(
        session, status="all" if principal.is_platform_admin else "published"
    )
    return Page(items=exams, next_cursor=None)


# The platform's own exams in every status, a page at a time, for the console.
@router.get(
    "/platform/exams",
    response_model=Page[schemas.ExamRead],
    responses=error_responses(Unauthenticated, Forbidden),
)
async def list_platform_exams(
    admin: PlatformAdmin,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    status: Annotated[
        str | None, Query(pattern="^(draft|published|retired)$", description="Filter by exam status")
    ] = None,
) -> Page[schemas.ExamRead]:
    _ = admin
    exams, next_cursor = await service_authoring.list_platform_exams(
        session, status=status, limit=page.limit, cursor=page.cursor
    )
    return Page(items=exams, next_cursor=next_cursor)


@router.post(
    "/platform/exams",
    response_model=schemas.ExamRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        Unauthenticated,
        Forbidden,
        errors.ExamCodeTaken,
        errors.InvalidExamCodeError,
        errors.InvalidExamSettings,
        errors.RubricVersionNotFound,
    ),
)
async def create_exam(body: schemas.CreateExam, admin: PlatformAdmin, session: Session) -> schemas.ExamRead:
    """A new platform exam, as a draft — the consumer catalogue."""
    return await service_authoring.create_exam(
        session,
        code=body.code,
        name=body.name,
        default_reading_seconds=body.default_reading_seconds,
        default_simulation_seconds=body.default_simulation_seconds,
        station_attempt_limit=body.station_attempt_limit,
        rubric_version_id=body.rubric_version_id,
        partner_pilot=body.partner_pilot,
        settings=body.settings,
    )


# Change a platform exam's name, timings or rubric. Its code cannot change.
@router.patch(
    "/platform/exams/{exam_id}",
    response_model=schemas.ExamRead,
    responses=error_responses(
        Unauthenticated,
        Forbidden,
        errors.UnknownExamError,
        errors.InvalidExamSettings,
        errors.RubricVersionNotFound,
        errors.ExamNotPublishable,
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
    workspace: OrgStaff,
    session: Session,
    status: Annotated[
        service_authoring.ExamListStatus,
        Query(description="published (default), draft or all"),
    ] = "published",
) -> Page[schemas.ExamRead]:
    """This institution's own exams, plus the platform catalogue, by `status`.

    The platform's own drafts are never included.
    """
    exams = await service_authoring.list_exams(session, org_id=workspace.org_id, status=status)
    return Page(items=exams, next_cursor=None)


# The platform's published exams, each marked with whether this institution already runs it.
@router.get(
    "/orgs/{org_slug}/exams/catalog",
    response_model=schemas.PlatformCatalogueRead,
    responses=error_responses(Forbidden),
)
async def list_platform_catalogue(workspace: OrgAdmin, session: Session) -> schemas.PlatformCatalogueRead:
    return schemas.PlatformCatalogueRead(
        items=await service_import.platform_catalogue(session, workspace.org_id)
    )


@router.post(
    "/orgs/{org_slug}/exams/import",
    response_model=schemas.ImportedExamRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.UnknownExamError, errors.ExamAlreadyImported),
)
async def import_platform_exam(
    body: schemas.ImportPlatformExam, workspace: OrgAdmin, session: Session
) -> schemas.ImportedExamRead:
    """Take on a published platform exam by reference: nothing is copied, a programme names it.

    `unknown_exam` (404) unless it is a published platform exam; `exam_already_imported`
    (409) if this institution already runs it.
    """
    exam = await service_import.import_platform_exam(
        session, workspace.org_id, platform_exam_id=body.platform_exam_id, actor=workspace.principal
    )
    return schemas.ImportedExamRead(exam=exam)


@router.post(
    "/orgs/{org_slug}/exams",
    response_model=schemas.ExamRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        Forbidden,
        errors.ExamCodeTaken,
        errors.InvalidExamCodeError,
        errors.InvalidExamSettings,
        errors.RubricVersionNotFound,
    ),
)
async def create_org_exam(
    body: schemas.CreateExam, workspace: OrgAdmin, session: Session
) -> schemas.ExamRead:
    """An institution's own exam, as a draft.

    The code is unique within this organisation only, so two schools may both
    have a `finals`.
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
        settings=body.settings,
    )


@router.patch(
    "/orgs/{org_slug}/exams/{exam_id}",
    response_model=schemas.ExamRead,
    responses=error_responses(
        Forbidden,
        errors.UnknownExamError,
        errors.InvalidExamSettings,
        errors.RubricVersionNotFound,
        errors.ExamNotPublishable,
    ),
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


@router.delete(
    "/orgs/{org_slug}/exams/{exam_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Forbidden, errors.UnknownExamError, errors.ExamInUse),
)
async def delete_org_exam(exam_id: uuid.UUID, workspace: OrgAdmin, session: Session) -> None:
    """Remove an exam nothing was ever built on. Retire the rest.

    Returns `exam_in_use` (409) if a station, sitting, attempt or rubric
    binding already references it.
    """
    await service_authoring.delete_exam(session, exam_id, workspace.org_id)


# The institution's own list of exams it runs, newest first.
@router.get(
    "/orgs/{org_slug}/programmes",
    response_model=Page[schemas.ProgrammeRead],
    responses=error_responses(Forbidden),
)
async def list_programmes(
    workspace: OrgStaff, session: Session, page: Annotated[CursorParams, Depends()]
) -> Page[schemas.ProgrammeRead]:
    programmes, next_cursor = await service_programmes.list_programmes(
        session, workspace.org_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=programmes, next_cursor=next_cursor)


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


# Pause or resume this institution's own programme.
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
