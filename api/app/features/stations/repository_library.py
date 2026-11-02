"""Queries against the platform's own half of the station table.

The library is the one body of stations that is nobody's — `owner_kind = 'platform'`,
`org_id IS NULL`. Every question asked of it is spelled the same way: narrow by exam or title, page
by the shared keyset cursor. The rest are the joins a bulk reader needs when it holds version ids
rather than stations.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection, Sequence
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ownership import visible_to
from app.core.pagination import keyset_page
from app.core.search import contains_text
from app.features.stations import domain
from app.features.stations.models import Station, StationVersion


def _first_published_at_floor() -> ColumnElement[bool]:
    """A correlated subquery for a station's earliest version `published_at`, compared against
    the date the old site started showing library stations.

    Pulled out once because four queries in this module apply the same floor to the same
    platform-library rows; a station that has never had a version published (so the subquery
    reads NULL) never passes it.
    """
    first_published_at = (
        select(func.min(StationVersion.published_at))
        .where(StationVersion.station_id == Station.id)
        .correlate(Station)
        .scalar_subquery()
    )
    return first_published_at >= domain.LIBRARY_FIRST_PUBLISHED_FLOOR


async def library_page(
    session: AsyncSession,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    exam_id: uuid.UUID | None = None,
    search: str | None = None,
    version_ids: Sequence[uuid.UUID] | None = None,
    station_ids: Sequence[uuid.UUID] | None = None,
    require_approved: bool = True,
    apply_date_floor: bool = True,
) -> tuple[list[Station], str | None]:
    """A page of the published library, narrowed by exam, by title, by current version and,
    when a plan limits the library, by which stations the limit allows.

    `search` belongs in SQL rather than in whoever asked: applying a filter to an already-fetched
    page can only ever match the rows that page contained. `require_approved` is the editor's
    sign-off gate on top of `status == 'published'`: turned off only for the staff console
    (`all_exams`), which has to find and review a published station nobody else may see yet.
    `apply_date_floor` hides stations first published before the old site's start date; staff
    turn it off too, as the old site let admins see everything.
    """
    stmt = select(Station).where(Station.owner_kind == "platform", Station.status == "published")
    if apply_date_floor:
        stmt = stmt.where(_first_published_at_floor())
    if require_approved:
        stmt = stmt.where(Station.approved.is_(True))
    if exam_id is not None:
        stmt = stmt.where(Station.exam_id == exam_id)
    if search and search.strip():
        # Matched like the console's other title filters, including its LIKE
        # wildcards: a `%` typed into a search box widens the query here too.
        stmt = stmt.where(contains_text(Station.title, search))
    if version_ids:
        stmt = stmt.where(Station.current_version_id.in_(list(version_ids)))
    if station_ids is not None:
        # Passed only when a plan limits the library: an empty collection here means the plan
        # allows nothing yet, not "no filter", so it must still narrow the query to nothing.
        stmt = stmt.where(Station.id.in_(list(station_ids)))
    return await keyset_page(
        session,
        stmt,
        sort_col=Station.created_at,
        id_col=Station.id,
        limit=limit,
        cursor=cursor,
        descending=False,
    )


async def first_station_ids(
    session: AsyncSession, *, exam_id: uuid.UUID, limit: int, exclude_ids: Collection[uuid.UUID] = ()
) -> list[uuid.UUID]:
    """The ids of the first `limit` approved, published platform-library stations of an exam past
    the date floor, oldest first by when each was first published, skipping `exclude_ids`.

    This is what a limited plan's window is built from: the earliest stations the person has not
    yet sat, enough to bring their total up to the plan's limit.
    """
    if limit <= 0:
        return []
    first_published_at = (
        select(func.min(StationVersion.published_at))
        .where(StationVersion.station_id == Station.id)
        .correlate(Station)
        .scalar_subquery()
    )
    stmt = (
        select(Station.id)
        .where(
            Station.owner_kind == "platform",
            Station.status == "published",
            Station.approved.is_(True),
            Station.exam_id == exam_id,
            Station.id.not_in(list(exclude_ids)),
            _first_published_at_floor(),
        )
        .order_by(first_published_at.asc(), Station.id.asc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars())


async def library_station(
    session: AsyncSession,
    station_id: uuid.UUID,
    *,
    require_approved: bool = True,
    apply_date_floor: bool = True,
) -> tuple[Station, StationVersion] | None:
    """One published library station with the version it currently points at.

    The join is the tenancy rule as well as the shape of the answer: a draft,
    an archived-never-published row, and any organisation's own station are all
    absent from the library, and this returns None for each rather than saying
    which. A station id is something a stranger may guess at, and the library
    answers only for the library's own. `require_approved` is the editor's
    sign-off gate, off only for staff (see `library_page`).
    """
    stmt = (
        select(Station, StationVersion)
        .join(StationVersion, StationVersion.id == Station.current_version_id)
        .where(
            Station.id == station_id,
            Station.owner_kind == "platform",
            Station.status == "published",
        )
    )
    if apply_date_floor:
        stmt = stmt.where(_first_published_at_floor())
    if require_approved:
        stmt = stmt.where(Station.approved.is_(True))
    pair = (await session.execute(stmt)).first()
    return (pair[0], pair[1]) if pair else None


async def versions_with_stations(
    session: AsyncSession, org_id: uuid.UUID | None, version_ids: Sequence[uuid.UUID]
) -> list[tuple[StationVersion, Station]]:
    """Several versions and the stations that own them, in one query.

    Scoped like `version_for_attempt`: the platform library is everybody's, an
    org's own stations are only its own. A circuit mixes both, which is why a
    console asking for its slots' station titles asks here once rather than
    resolving each id through the station routes.
    """
    if not version_ids:
        return []
    owner = visible_to(Station, org_id)
    stmt = (
        select(StationVersion, Station)
        .join(Station, Station.id == StationVersion.station_id)
        .where(StationVersion.id.in_(list(version_ids)), owner)
    )
    return [(version, station) for version, station in (await session.execute(stmt)).all()]


async def published_library_versions(
    session: AsyncSession, *, exam_id: uuid.UUID | None = None, require_approved: bool = True
) -> list[tuple[StationVersion, Station]]:
    """Every current, published platform-library version, with its station.

    The whole library at once rather than a page, because the only caller is a
    re-index that has to see all of it: a paged walk of a table being written
    to can miss a row or read one twice, and either leaves the index quietly
    wrong about material nobody will check. `require_approved` is the editor's sign-off gate
    (see `library_page`); every current caller is picking or indexing material for a reader
    rather than for staff, so it stays on.
    """
    stmt = (
        select(StationVersion, Station)
        .join(Station, Station.id == StationVersion.station_id)
        .where(
            Station.owner_kind == "platform",
            Station.status == "published",
            StationVersion.status == "published",
            StationVersion.id == Station.current_version_id,
            _first_published_at_floor(),
        )
    )
    if require_approved:
        stmt = stmt.where(Station.approved.is_(True))
    if exam_id is not None:
        stmt = stmt.where(Station.exam_id == exam_id)
    return [(version, station) for version, station in (await session.execute(stmt)).all()]


async def published_counts_by_exam(
    session: AsyncSession, exam_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """How many published, approved library stations each of these exams has, in one grouped query.

    An exam with none is absent from the answer rather than present with zero; the caller
    reads it with a default. Filtered by approval like the rest of the library: both of its
    current callers (the institution import catalogue and the public pricing page) are a count
    someone outside the platform is about to rely on, not a staff worklist, so an unapproved
    station must not be counted in either.
    """
    if not exam_ids:
        return {}
    stmt = (
        select(Station.exam_id, func.count())
        .where(
            Station.owner_kind == "platform",
            Station.status == "published",
            Station.approved.is_(True),
            Station.exam_id.in_(list(exam_ids)),
            _first_published_at_floor(),
        )
        .group_by(Station.exam_id)
    )
    return {exam_id: int(station_count) for exam_id, station_count in (await session.execute(stmt)).all()}
