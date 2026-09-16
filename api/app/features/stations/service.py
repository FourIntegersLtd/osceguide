"""Station authoring use cases.

The lifecycle decisions come from `domain.py`; this maps them onto storage and
translates the domain's refusals into API error codes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog.errors import UnknownExamError as CatalogUnknownExam
from app.features.catalog.service import resolve_exam
from app.features.stations import domain, errors, repository
from app.features.stations.models import Station, StationVersion
from app.features.stations.schemas import StationRead, StationVersionRead

# One place mapping a domain refusal to its API code, so a new rule does not
# need a new `except` clause in every caller.
_REFUSALS: dict[type[domain.LifecycleError], type[Exception]] = {
    domain.NotEditable: errors.NotEditableError,
    domain.NotDeletable: errors.NotDeletableError,
    domain.AlreadyPublished: errors.AlreadyPublishedError,
    domain.NotArchivable: errors.NotArchivableError,
    domain.TemplateNotPublished: errors.TemplateNotPublishedError,
    domain.StationNotPublished: errors.NotEditableError,
}


def _raise(exc: domain.LifecycleError) -> None:
    mapped = _REFUSALS.get(type(exc), errors.NotEditableError)
    raise mapped(str(exc)) from exc


async def create_station(
    session: AsyncSession, org_id: uuid.UUID, *, title: str, exam_code: str, content: dict[str, Any]
) -> StationRead:
    try:
        exam = await resolve_exam(session, exam_code)
    except CatalogUnknownExam as exc:
        # Re-raised as this slice's type so the router documents its own errors.
        raise errors.UnknownExamError(str(exc)) from exc
    station = await repository.create_station(session, org_id, exam_id=exam.id, title=title)
    version = await repository.add_version(session, org_id, station_id=station.id, version=1, content=content)
    return _station_read(station, exam.code, version)


async def read_station(session: AsyncSession, org_id: uuid.UUID, station_id: uuid.UUID) -> Station:
    station = await repository.station_by_id(session, org_id, station_id)
    if station is None:
        raise errors.StationNotFound()
    return station


async def add_version(session: AsyncSession, org_id: uuid.UUID, station_id: uuid.UUID) -> StationVersionRead:
    """Open a new draft, seeded from the latest published version."""
    await read_station(session, org_id, station_id)
    existing = await repository.versions_for_station(session, org_id, station_id)
    refs = [domain.VersionRef(number=v.version, status=domain.Status(v.status)) for v in existing]
    seed = domain.seed_version(refs)
    content: dict[str, Any] = {}
    if seed is not None:
        source = next(v for v in existing if v.version == seed.number)
        content = dict(source.content)
    row = await repository.add_version(
        session,
        org_id,
        station_id=station_id,
        version=domain.next_version_number(refs),
        content=content,
    )
    return _version_read(row)


async def edit_version(
    session: AsyncSession,
    org_id: uuid.UUID,
    station_id: uuid.UUID,
    version: int,
    *,
    content: dict[str, Any],
) -> StationVersionRead:
    row = await _version(session, org_id, station_id, version)
    try:
        domain.ensure_editable(domain.VersionRef(number=row.version, status=domain.Status(row.status)))
    except domain.LifecycleError as exc:
        _raise(exc)
    await repository.set_version_content(session, org_id, row.id, content=content)
    return _version_read(await _version(session, org_id, station_id, version))


async def publish_version(
    session: AsyncSession,
    org_id: uuid.UUID,
    station_id: uuid.UUID,
    version: int,
    *,
    actor_id: uuid.UUID,
    now: datetime,
) -> StationVersionRead:
    row = await _version(session, org_id, station_id, version)
    try:
        new_status = domain.publish(domain.VersionRef(number=row.version, status=domain.Status(row.status)))
    except domain.LifecycleError as exc:
        _raise(exc)
    await repository.set_version_status(session, org_id, row.id, status=str(new_status), at=now, by=actor_id)
    # The station points at its newest published version, so a circuit can
    # reference the station and still get a frozen revision.
    await repository.set_current_version(session, org_id, station_id, version_id=row.id)
    return _version_read(await _version(session, org_id, station_id, version))


async def archive_version(
    session: AsyncSession,
    org_id: uuid.UUID,
    station_id: uuid.UUID,
    version: int,
    *,
    actor_id: uuid.UUID,
    now: datetime,
) -> StationVersionRead:
    row = await _version(session, org_id, station_id, version)
    try:
        new_status = domain.archive(domain.VersionRef(number=row.version, status=domain.Status(row.status)))
    except domain.LifecycleError as exc:
        _raise(exc)
    await repository.set_version_status(session, org_id, row.id, status=str(new_status), at=now, by=actor_id)
    return _version_read(await _version(session, org_id, station_id, version))


async def list_stations(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[StationRead], str | None]:
    rows, next_cursor = await repository.list_for_org(session, org_id, limit=limit, cursor=cursor)
    out = []
    for station in rows:
        versions = await repository.versions_for_station(session, org_id, station.id)
        latest = versions[-1] if versions else None
        exam = await _exam_code(session, station)
        out.append(_station_read(station, exam, latest))
    return out, next_cursor


async def _version(
    session: AsyncSession, org_id: uuid.UUID, station_id: uuid.UUID, version: int
) -> StationVersion:
    await read_station(session, org_id, station_id)
    row = await repository.version_by_number(session, org_id, station_id, version)
    if row is None:
        raise errors.VersionNotFound()
    return row


async def _exam_code(session: AsyncSession, station: Station) -> str:
    from app.features.catalog import repository as catalog_repo

    exam = await catalog_repo.exam_by_id(session, station.exam_id)
    return exam.code if exam else ""


def _station_read(station: Station, exam_code: str, version: StationVersion | None) -> StationRead:
    return StationRead(
        id=station.id,
        title=station.title,
        owner_kind=station.owner_kind,
        exam_code=exam_code,
        status=version.status if version else station.status,
        version=version.version if version else 0,
        content=dict(version.content) if version else None,
        current_version_id=station.current_version_id,
    )


def _version_read(row: StationVersion) -> StationVersionRead:
    return StationVersionRead(
        id=row.id,
        station_id=row.station_id,
        version=row.version,
        status=row.status,
        content=dict(row.content),
        published_at=row.published_at,
    )


@dataclass(frozen=True)
class RunnableStation:
    """A station resolved for an attempt to run against."""

    version_id: uuid.UUID
    owner_kind: str
    exam_code: str
    title: str
    content: dict[str, Any]
    published: bool


async def runnable_station(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> RunnableStation | None:
    """Resolve the station an attempt will be rendered from.

    Lives here because this slice owns what a station looks like. `attempts`
    asks for a scenario and never learns the shape of one, which is the same
    boundary the worker sits behind.
    """
    found = await repository.version_for_attempt(session, org_id, version_id)
    if found is None:
        return None
    version, station = found
    return RunnableStation(
        version_id=version.id,
        owner_kind=station.owner_kind,
        exam_code=await _exam_code(session, station),
        title=station.title,
        content=dict(version.content or {}),
        published=version.status == "published",
    )
