"""The platform's own station library, and the templates behind it.

The same services the org routes use, with `org_id=None`. An org may read and build on what is
published here; only a platform admin may write it. `OrgAdmin` sets `allow_platform_admin=False`,
so the reverse holds too — neither can author the other's content.

The two reads that answer for one station named by id — `GET /stations/{id}` and
`GET /stations/{id}/versions` — live here too, since they belong to the library rather than to an
organisation's slug. Their authorisation is per route: one is for any reader entitled to the
station's exam, the other for staff.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, InvalidInput, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.schemas import StationReview
from app.core.settings import SettingsDep
from app.core.tenancy import PlatformAdmin
from app.features.stations import (
    errors,
    schemas,
    service,
    service_facts,
    service_library_reads,
    service_versions,
    station_autogenerate,
)

router = APIRouter(tags=["stations"])

Session = Annotated[AsyncSession, Depends(get_session)]

_AUTH = (Unauthenticated, Forbidden)
_STATION = (errors.StationNotFound, errors.VersionNotFound)
_LIFECYCLE = (
    errors.NotEditableError,
    errors.AlreadyPublishedError,
    errors.NotArchivableError,
    errors.NotDeletableError,
)


# --- the library ------------------------------------------------------------


@router.get(
    "/platform/stations",
    response_model=Page[schemas.StationRead],
    responses=error_responses(*_AUTH),
)
async def list_platform_stations(
    admin: PlatformAdmin,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    search: str | None = None,
    exam_code: str | None = None,
    include_archived: bool = False,
) -> Page[schemas.StationRead]:
    """Every library station, drafts included — the author's own view of it.

    Archived stations are left out unless `include_archived` is set.
    """
    items, next_cursor = await service.list_stations(
        session,
        None,
        limit=page.limit,
        cursor=page.cursor,
        full_content=True,
        search=search,
        exam_code=exam_code,
        include_archived=include_archived,
    )
    return Page(items=items, next_cursor=next_cursor)


# Author a new library station on a platform template version.
@router.post(
    "/platform/stations",
    response_model=schemas.StationRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        *_AUTH,
        errors.UnknownExamError,
        errors.StationTemplateVersionNotFound,
        errors.TemplateNotPublishedError,
    ),
)
async def create_platform_station(
    body: schemas.CreateStation, admin: PlatformAdmin, session: Session
) -> schemas.StationRead:
    return await service.create_station(
        session,
        None,
        title=body.title,
        exam_code=body.exam_code,
        content=body.content,
        template_version_id=body.template_version_id,
    )


# Draft a new library station's content from a prompt, against a platform template version.
@router.post(
    "/platform/stations/autogenerate-draft",
    response_model=schemas.AutogenerateStationDraftResult,
    responses=error_responses(
        *_AUTH,
        InvalidInput,
        errors.GenerationUnavailable,
        errors.StationTemplateVersionNotFound,
        errors.TemplateNotPublishedError,
    ),
)
async def autogenerate_platform_station_draft(
    body: schemas.AutogenerateStationDraft,
    admin: PlatformAdmin,
    session: Session,
    settings: SettingsDep,
) -> schemas.AutogenerateStationDraftResult:
    _ = admin
    draft_result = await station_autogenerate.autogenerate_station_draft(
        session,
        None,
        prompt=body.prompt,
        template_version_id=body.template_version_id,
        settings=settings,
    )
    return schemas.AutogenerateStationDraftResult(**draft_result)


# Add a new version to a platform station.
@router.post(
    "/platform/stations/{station_id}/versions",
    response_model=schemas.StationVersionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(*_AUTH, *_STATION, errors.DraftExistsError),
)
async def add_platform_station_version(
    station_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.StationVersionRead:
    return await service_versions.add_version(session, None, station_id)


# Throw away a draft; a station whose only version it was goes too.
@router.delete(
    "/platform/stations/{station_id}/versions/{version}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(*_AUTH, *_STATION, errors.NotDeletableError),
)
async def delete_platform_station_version(
    station_id: uuid.UUID, version: int, admin: PlatformAdmin, session: Session
) -> None:
    """Only a draft: a published version is what an attempt was assessed against, so it is archived."""
    await service_versions.delete_version(session, None, station_id, version, actor=admin)


# Edit the content of one version of a platform station.
@router.patch(
    "/platform/stations/{station_id}/versions/{version}",
    response_model=schemas.StationVersionRead,
    responses=error_responses(*_AUTH, *_STATION, errors.NotEditableError, errors.StationBeingProduced),
)
async def edit_platform_station_version(
    station_id: uuid.UUID,
    version: int,
    body: schemas.UpdateVersion,
    admin: PlatformAdmin,
    session: Session,
) -> schemas.StationVersionRead:
    return await service_versions.edit_version(
        session, None, station_id, version, content=body.content, facts=body.facts, title=body.title
    )


@router.get(
    "/platform/stations/{station_id}/versions/{version}/review",
    response_model=StationReview,
    responses=error_responses(*_AUTH, *_STATION),
)
async def read_platform_station_review(
    station_id: uuid.UUID, version: int, admin: PlatformAdmin, session: Session
) -> StationReview:
    """The version's fact check, if one has been run."""
    return await service_facts.read_review(session, station_id, version)


@router.post(
    "/platform/stations/{station_id}/versions/{version}/check-facts",
    response_model=StationReview,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(*_AUTH, *_STATION, errors.FactCheckRunning, errors.StationBeingProduced),
)
async def check_platform_station_facts(
    station_id: uuid.UUID, version: int, admin: PlatformAdmin, session: Session
) -> StationReview:
    """Starts checking the version's clinical claims; `station.updated` says when it settles."""
    return await service_facts.enqueue_check(session, station_id, version, requested_by=admin.user_id)


@router.post(
    "/platform/stations/{station_id}/versions/{version}/publish",
    response_model=schemas.StationVersionRead,
    responses=error_responses(*_AUTH, *_STATION, *_LIFECYCLE),
)
async def publish_platform_station_version(
    station_id: uuid.UUID, version: int, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.StationVersionRead:
    """Publish it into the library, where every organisation may draw on it."""
    return await service_versions.publish_version(
        session, None, station_id, version, actor_id=admin.user_id, now=clock.now()
    )


# Retire a published library station version so it can no longer be scheduled.
@router.post(
    "/platform/stations/{station_id}/versions/{version}/archive",
    response_model=schemas.StationVersionRead,
    responses=error_responses(*_AUTH, *_STATION, *_LIFECYCLE),
)
async def archive_platform_station_version(
    station_id: uuid.UUID, version: int, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.StationVersionRead:
    return await service_versions.archive_version(
        session, None, station_id, version, now=clock.now(), actor=admin
    )


# --- one station, named by id ------------------------------------------------


@router.get(
    "/stations/{station_id}",
    response_model=schemas.LibraryStationRead,
    responses=error_responses(Unauthenticated, errors.StationNotFound, errors.NotEntitled),
)
async def read_library_station(
    station_id: uuid.UUID, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.LibraryStationRead:
    """One station from the platform library: a title and the ids needed to bind it, not the document.

    One refusal covers every station that is not the library's — another institution's private case
    and a draft nobody has published answer identically.
    """
    return await service_library_reads.read_library_station(
        session,
        station_id,
        user_id=principal.user_id,
        now=clock.now(),
        all_exams=principal.is_platform_admin,
    )


@router.get(
    "/stations/{station_id}/versions",
    response_model=list[schemas.StationVersionRead],
    responses=error_responses(Unauthenticated, Forbidden, errors.StationNotFound),
)
async def station_version_history(
    station_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> list[schemas.StationVersionRead]:
    """Every revision this station has had, newest first — whole documents, so staff-only.

    See `service_versions` for the audience rule.
    """
    return await service_versions.version_history(session, station_id, caller=principal)
