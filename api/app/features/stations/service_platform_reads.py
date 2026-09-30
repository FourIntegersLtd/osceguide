"""What the console may read about a station regardless of who owns it."""

from __future__ import annotations

import uuid
from collections.abc import Collection
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import service as catalog
from app.features.stations import repository


@dataclass(frozen=True)
class StationVersions:
    """A station and every revision of it, as ids the console acts on."""

    station_id: uuid.UUID
    title: str
    exam_code: str
    version_ids: list[uuid.UUID]


async def station_versions(session: AsyncSession, station_id: uuid.UUID) -> StationVersions | None:
    """One station and its version ids, whoever owns it, or `None` if there is no such station."""
    found = await repository.station_with_versions(session, station_id)
    if found is None:
        return None
    station, versions = found
    code = await catalog.exam_code_by_id(session, station.exam_id)
    return StationVersions(
        station_id=station.id,
        title=station.title,
        exam_code=code or "",
        version_ids=[version.id for version in versions],
    )


@dataclass(frozen=True)
class VersionOwner:
    """Which station a version belongs to, for a row that stores the version."""

    version_id: uuid.UUID
    station_id: uuid.UUID
    title: str
    exam_code: str


async def owners_by_version_id(
    session: AsyncSession, version_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, VersionOwner]:
    """Which station owns each of these versions, in one query, whoever owns the station."""
    owner_pairs = await repository.versions_with_stations_any_owner(session, version_ids)
    codes = await catalog.exam_codes_by_id(session, list({station.exam_id for _, station in owner_pairs}))
    return {
        version.id: VersionOwner(
            version_id=version.id,
            station_id=station.id,
            title=station.title,
            exam_code=codes.get(station.exam_id, ""),
        )
        for version, station in owner_pairs
    }
