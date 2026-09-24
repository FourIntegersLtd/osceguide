"""The platform's own station library, and the templates behind it.

The same services the org routes use, with `org_id=None`. Until now the
platform half of `stations` had no write path at all: the library was inserted
by a legacy import or by hand, and the four exams' station shapes lived in the
engine as formatters chosen by a branch on the exam's code.

An org may read and build on what is published here; only a platform admin may
write it. `OrgAdmin` sets `allow_platform_admin=False`, so the reverse holds
too — neither can author the other's content.

The two reads that answer for one station named by id — `GET /stations/{id}`
and `GET /stations/{id}/versions` — are here as well, at the tail of the file.
They belong to the library rather than to an organisation's slug, and
`router.py`, which holds the browse page they share the library's rule with, is
at the slice's line cap. Their authorisation is per route, not per file: one is
for any reader entitled to the station's exam, and the other for staff.
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
from app.core.settings import SettingsDep
from app.core.tenancy import PlatformAdmin
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
) -> Page[schemas.StationRead]:
    """Every library station, drafts included — the author's own view of it."""
    items, next_cursor = await service.list_stations(
        session, None, limit=page.limit, cursor=page.cursor, full_content=True, search=search
    )
    return Page(items=items, next_cursor=next_cursor)


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
    result = await station_autogenerate.autogenerate_station_draft(
        session,
        None,
        prompt=body.prompt,
        template_version_id=body.template_version_id,
        settings=settings,
    )
    return schemas.AutogenerateStationDraftResult(**result)


@router.post(
    "/platform/stations/{station_id}/versions",
    response_model=schemas.StationVersionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(*_AUTH, *_STATION),
)
async def add_platform_station_version(
    station_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.StationVersionRead:
    return await service_versions.add_version(session, None, station_id)


@router.patch(
    "/platform/stations/{station_id}/versions/{version}",
    response_model=schemas.StationVersionRead,
    responses=error_responses(*_AUTH, *_STATION, errors.NotEditableError),
)
async def edit_platform_station_version(
    station_id: uuid.UUID,
    version: int,
    body: schemas.UpdateVersion,
    admin: PlatformAdmin,
    session: Session,
) -> schemas.StationVersionRead:
    return await service_versions.edit_version(session, None, station_id, version, content=body.content)


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


@router.post(
    "/platform/stations/{station_id}/versions/{version}/archive",
    response_model=schemas.StationVersionRead,
    responses=error_responses(*_AUTH, *_STATION, *_LIFECYCLE),
)
async def archive_platform_station_version(
    station_id: uuid.UUID, version: int, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.StationVersionRead:
    return await service_versions.archive_version(
        session, None, station_id, version, actor_id=admin.user_id, now=clock.now()
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
    """One station from the platform library, for whoever a link found them to be.

    The row the browse page already gives — a title and the ids needed to bind
    it — and none of the document inside it. A shared link used to be answered
    by walking that page a hundred stations at a time in the browser, because
    there was no read that took an id and no organisation's slug.

    One refusal covers every station that is not the library's: another
    institution's private case and a draft nobody has published answer
    identically, because which of them it was is somebody else's tenant.
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
    """Every revision this station has had, newest first. The author's own view.

    The lifecycle had no reader: a station could be drafted, published,
    superseded and archived, and nothing listed the revisions those acts
    produced — so the authoring screen could not offer a previous one. Whole
    documents, which is why the audience is staff and not the station's org
    members at large (the rule, and why, are in `service_versions`).
    """
    return await service_versions.version_history(session, station_id, caller=principal)
