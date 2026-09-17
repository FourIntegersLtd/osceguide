"""Bulk answers about stations, for the screens that show many at once.

Split from `service.py` by concept rather than by line count: everything here
answers "tell me about these stations" for a caller that already holds a set of
ids — a console listing a circuit's slots, a dashboard counting a library. The
use cases in `service.py` act on one station at a time and enforce its
lifecycle; nothing here changes anything.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import service as catalog
from app.features.stations import repository
from app.features.stations.schemas import LibraryStationRead


@dataclass(frozen=True)
class StationSummary:
    """A station version as a row on somebody else's screen."""

    version_id: uuid.UUID
    station_id: uuid.UUID
    title: str
    version: int
    status: str
    owner_kind: str
    published_at: datetime | None


async def summaries_by_version_id(
    session: AsyncSession, org_id: uuid.UUID | None, version_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, StationSummary]:
    """Titles for a set of station versions, keyed by version id.

    The frontend resolves these one id at a time against the catalogue — the
    N+1 the read models exist to delete.
    """
    rows = await repository.versions_with_stations(session, org_id, list(version_ids))
    return {
        version.id: StationSummary(
            version_id=version.id,
            station_id=station.id,
            title=station.title,
            version=version.version,
            status=version.status,
            owner_kind=station.owner_kind,
            published_at=version.published_at,
        )
        for version, station in rows
    }


async def count_stations(session: AsyncSession, org_id: uuid.UUID | None) -> int:
    """How many stations this organisation has authored."""
    return await repository.count_for_org(session, org_id)


async def browse_library(
    session: AsyncSession,
    *,
    exam_code: str | None,
    limit: int,
    cursor: dict[str, Any] | None,
) -> tuple[list[LibraryStationRead], str | None]:
    """The published platform library, for anybody signed in.

    The `owner_kind = 'platform'` half of the table had no reader at all: a
    consumer could build a practice set only out of station version ids they
    had no way to discover. An unpublished station is not in the library, and
    neither is any organisation's own — those are behind the org routes.
    """
    exam_id = None
    if exam_code is not None:
        exam_id = (await catalog.resolve_exam(session, exam_code)).id

    rows, next_cursor = await repository.list_platform_library(
        session, limit=limit, cursor=cursor, exam_id=exam_id
    )
    version_ids = [row.current_version_id for row in rows if row.current_version_id is not None]
    versions = await summaries_by_version_id(session, None, version_ids)
    codes = await catalog.exam_codes_by_id(session, [row.exam_id for row in rows])

    out: list[LibraryStationRead] = []
    for row in rows:
        version = versions.get(row.current_version_id) if row.current_version_id else None
        # A published station with no current version is a seeding fault, not
        # something a browser can act on: there is nothing for it to bind.
        if version is None:
            continue
        out.append(
            LibraryStationRead(
                id=row.id,
                title=row.title,
                exam_code=codes.get(row.exam_id, ""),
                version_id=version.version_id,
                version=version.version,
                published_at=version.published_at,
            )
        )
    return out, next_cursor
