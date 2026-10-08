"""Routes for authoring a station and browsing the platform library: creating a station, adding,
editing, publishing and archiving its versions, and correcting a published version's reading brief.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, InvalidInput, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.settings import SettingsDep
from app.core.tenancy import OrgAdmin, OrgReader, OrgStaff, may_run_circuit_policy
from app.features.stations import (
    errors,
    schemas,
    service,
    service_library_reads,
    service_versions,
    station_autogenerate,
)

router = APIRouter(tags=["stations"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/stations",
    response_model=Page[schemas.LibraryStationRead],
    responses=error_responses(Unauthenticated, errors.UnknownExamError, errors.NotEntitled),
)
async def browse_library(
    principal: CurrentPrincipal,
    session: Session,
    clock: ClockDep,
    page: Annotated[CursorParams, Depends()],
    exam_code: str | None = None,
    search: str | None = None,
    version_ids: Annotated[
        list[uuid.UUID] | None,
        Query(
            max_length=100,
            description="Only stations whose current version is one of these (repeat the param).",
        ),
    ] = None,
) -> Page[schemas.LibraryStationRead]:
    """The published platform library, scoped to what the caller may open.

    Rows carry no station content — see `LibraryStationRead`. `search` matches a title fragment in
    SQL; `version_ids` narrows to the stations those versions are current for. A platform admin
    browses the whole catalogue; everybody else gets their own exam, and asking for another is
    refused.
    """
    items, next_cursor = await service_library_reads.browse_library(
        session,
        exam_code=exam_code,
        limit=page.limit,
        cursor=page.cursor,
        user_id=principal.user_id,
        now=clock.now(),
        all_exams=principal.is_platform_admin,
        search=search,
        version_ids=version_ids,
        staff_org_ids=[
            membership.org_id
            for membership in principal.memberships
            if may_run_circuit_policy()(membership.role)
        ],
    )
    return Page(items=items, next_cursor=next_cursor)


@router.get(
    "/orgs/{org_slug}/stations",
    response_model=Page[schemas.StationRead],
    responses=error_responses(Forbidden),
)
async def list_stations(
    workspace: OrgReader,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    search: str | None = None,
    exam_code: str | None = None,
    include_archived: bool = False,
) -> Page[schemas.StationRead]:
    """The stations this organisation has authored.

    `OrgReader` admits every rostered trainee, who gets the candidate-facing projection of each
    `content` (S1) rather than the patient's persona and examiner's notes. Staff and a platform
    admin read the whole thing. Archived stations are left out unless `include_archived` is set.
    """
    items, next_cursor = await service.list_stations(
        session,
        workspace.org_id,
        limit=page.limit,
        cursor=page.cursor,
        full_content=workspace.is_platform_admin or may_run_circuit_policy()(workspace.role),
        search=search,
        exam_code=exam_code,
        include_archived=include_archived,
    )
    return Page(items=items, next_cursor=next_cursor)


@router.get(
    "/orgs/{org_slug}/station-versions/{version_id}/sections",
    response_model=list[schemas.AudienceSectionRead],
    responses=error_responses(Forbidden, errors.VersionNotFound),
)
async def read_staff_sections(
    workspace: OrgStaff, session: Session, version_id: uuid.UUID
) -> list[schemas.AudienceSectionRead]:
    """A station version as the staff running a sitting read it: every audience's sections.

    The candidate's brief, the patient's script with what they hold back, the
    examiner's notes and the faculty's own material. Empty for a station bound
    to no template.
    """
    return await service.staff_sections(session, workspace.org_id, version_id)


# Author a new station on this org's own template version.
@router.post(
    "/orgs/{org_slug}/stations",
    response_model=schemas.StationRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        Forbidden,
        errors.UnknownExamError,
        errors.StationTemplateVersionNotFound,
        errors.TemplateNotPublishedError,
    ),
)
async def create_station(
    body: schemas.CreateStation, workspace: OrgAdmin, session: Session
) -> schemas.StationRead:
    return await service.create_station(
        session,
        workspace.org_id,
        title=body.title,
        exam_code=body.exam_code,
        content=body.content,
        template_version_id=body.template_version_id,
    )


# Draft a new station's content from a prompt, against this org's template version.
@router.post(
    "/orgs/{org_slug}/stations/autogenerate-draft",
    response_model=schemas.AutogenerateStationDraftResult,
    responses=error_responses(
        Forbidden,
        InvalidInput,
        errors.GenerationUnavailable,
        errors.StationTemplateVersionNotFound,
        errors.TemplateNotPublishedError,
    ),
)
async def autogenerate_station_draft(
    body: schemas.AutogenerateStationDraft,
    workspace: OrgAdmin,
    session: Session,
    settings: SettingsDep,
) -> schemas.AutogenerateStationDraftResult:
    draft_result = await station_autogenerate.autogenerate_station_draft(
        session,
        workspace.org_id,
        prompt=body.prompt,
        template_version_id=body.template_version_id,
        settings=settings,
    )
    return schemas.AutogenerateStationDraftResult(**draft_result)


# Add a new version to one of an organisation's stations.
@router.post(
    "/orgs/{org_slug}/stations/{station_id}/versions",
    response_model=schemas.StationVersionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.StationNotFound),
)
async def add_version(
    station_id: uuid.UUID, workspace: OrgAdmin, session: Session
) -> schemas.StationVersionRead:
    return await service_versions.add_version(session, workspace.org_id, station_id)


# Overwrite a draft version's content.
@router.patch(
    "/orgs/{org_slug}/stations/{station_id}/versions/{version}",
    response_model=schemas.StationVersionRead,
    responses=error_responses(
        Forbidden, errors.VersionNotFound, errors.StationNotFound, errors.NotEditableError
    ),
)
async def edit_version(
    station_id: uuid.UUID,
    version: int,
    body: schemas.UpdateVersion,
    workspace: OrgAdmin,
    session: Session,
) -> schemas.StationVersionRead:
    return await service_versions.edit_version(
        session, workspace.org_id, station_id, version, content=body.content, title=body.title
    )


# Publish a draft version. A station's patient material must never reach a trainee before their
# attempt, so nothing may schedule this station's earlier drafts once this happens.
@router.post(
    "/orgs/{org_slug}/stations/{station_id}/versions/{version}/publish",
    response_model=schemas.StationVersionRead,
    responses=error_responses(
        Forbidden, errors.VersionNotFound, errors.AlreadyPublishedError, errors.StationEmptyError
    ),
)
async def publish_version(
    station_id: uuid.UUID, version: int, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.StationVersionRead:
    return await service_versions.publish_version(
        session,
        workspace.org_id,
        station_id,
        version,
        actor_id=workspace.principal.user_id,
        now=clock.now(),
    )


# Retire a published version so it can no longer be scheduled.
@router.post(
    "/orgs/{org_slug}/stations/{station_id}/versions/{version}/archive",
    response_model=schemas.StationVersionRead,
    responses=error_responses(Forbidden, errors.VersionNotFound, errors.NotArchivableError),
)
async def archive_version(
    station_id: uuid.UUID, version: int, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.StationVersionRead:
    return await service_versions.archive_version(
        session,
        workspace.org_id,
        station_id,
        version,
        now=clock.now(),
        actor=workspace.principal,
    )


@router.delete(
    "/orgs/{org_slug}/stations/{station_id}/versions/{version}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Forbidden, errors.VersionNotFound, errors.NotDeletableError),
)
async def delete_version(station_id: uuid.UUID, version: int, workspace: OrgAdmin, session: Session) -> None:
    """Throw away a draft. A published version is what an attempt was assessed
    against, so it is archived instead, never deleted."""
    await service_versions.delete_version(
        session, workspace.org_id, station_id, version, actor=workspace.principal
    )


@router.patch(
    "/orgs/{org_slug}/stations/{station_id}/versions/{version}/brief",
    response_model=schemas.StationVersionRead,
    responses=error_responses(Forbidden, errors.VersionNotFound, errors.NotEditableError),
)
async def edit_brief(
    station_id: uuid.UUID,
    version: int,
    body: schemas.UpdateBrief,
    workspace: OrgAdmin,
    session: Session,
) -> schemas.StationVersionRead:
    """Correct the reading brief without cutting a new version (T5).

    The brief is what a candidate is handed before the station starts —
    presentation, not assessed content — so a typo in one does not invalidate
    what everybody else was marked against.
    """
    return await service_versions.edit_brief(
        session, workspace.org_id, station_id, version, brief=body.reading_brief
    )
