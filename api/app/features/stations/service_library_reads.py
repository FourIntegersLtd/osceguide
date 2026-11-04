"""Reading the platform library: the browse page, and one station from it.

A library row is a title and the ids needed to bind it, never the document inside it. A link is
still browsing, and browsing is not reading the answers.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import cache
from app.core.settings import get_settings
from app.features.catalog import service as catalog
from app.features.entitlements import service_access
from app.features.stations import domain, errors, repository_library, service_plan_window
from app.features.stations.schemas import LibraryStationRead
from app.features.stations.service_reads import summaries_by_version_id

_PAGE = TypeAdapter(tuple[list[LibraryStationRead], str | None])


async def browse_library(
    session: AsyncSession,
    *,
    exam_code: str | None,
    limit: int,
    cursor: dict[str, Any] | None,
    user_id: uuid.UUID | None = None,
    now: datetime | None = None,
    all_exams: bool = False,
    search: str | None = None,
    version_ids: list[uuid.UUID] | None = None,
    staff_org_ids: Iterable[uuid.UUID] = (),
) -> tuple[list[LibraryStationRead], str | None]:
    """The published platform library, scoped to the exams the caller may open.

    An unpublished station is not in the library, and neither is any organisation's own — those are
    behind the org routes. A named `exam_code` must be one the caller may open; without one they get
    theirs. `all_exams` is the staff console, which curates the whole catalogue explicitly rather
    than by omission. `search` matches a title fragment, answered in SQL. `staff_org_ids` are the
    organisations the caller runs circuits for: an exam one of them offers is browsable for building
    that organisation's circuit, whatever the staff member holds as a consumer.
    """
    exam_id = None
    resolved_exam_code = exam_code
    if exam_code is not None:
        exam_id = (await catalog.resolve_exam(session, exam_code)).id
        if (
            user_id is not None
            and now is not None
            and not all_exams
            and not await _offered_by_any(session, staff_org_ids, exam_id)
        ):
            await service_access.require_exam_access(session, user_id, exam_code=exam_code, now=now)
    elif user_id is not None and now is not None and not all_exams:
        # No exam named: theirs, rather than everybody's.
        access = await service_access.exam_access_for(session, user_id, now=now)
        if access.current is None:
            # Nothing they may open, so nothing to browse. An empty page rather than
            # a refusal: a brand-new account with no exam chosen has no library yet.
            return [], None
        resolved_exam_code = access.current
        exam_id = (await catalog.resolve_exam(session, access.current)).id

    # A plan's station limit only ever narrows a signed-in consumer's own browse of their own
    # exam; staff curating the whole catalogue (`all_exams`) are never capped by it.
    plan_station_ids: set[uuid.UUID] | None = None
    if (
        user_id is not None
        and now is not None
        and not all_exams
        and exam_id is not None
        and resolved_exam_code
    ):
        plan_station_ids = await service_plan_window.allowed_station_ids(
            session, user_id=user_id, exam_id=exam_id, exam_code=resolved_exam_code, now=now
        )

    async def load() -> tuple[list[LibraryStationRead], str | None]:
        """Read this page of the library from the database."""
        return await _load_page(
            session,
            limit=limit,
            cursor=cursor,
            exam_id=exam_id,
            search=search,
            version_ids=version_ids,
            station_ids=list(plan_station_ids) if plan_station_ids is not None else None,
            all_exams=all_exams,
        )

    if plan_station_ids is not None:
        # A plan's window differs per person, so only the shared page is cached.
        return await load()
    shape = json.dumps(
        [search, sorted(str(version_id) for version_id in version_ids or []), cursor, limit, all_exams],
        sort_keys=True,
        default=str,
    )
    digest = hashlib.sha1(shape.encode(), usedforsecurity=False).hexdigest()
    scope = domain.library_cache_scope(exam_id)
    return await cache.get_or_load(
        f"{scope}:page:{digest}:v{await cache.version(scope)}",
        get_settings().library_cache_seconds,
        load,
        dump=lambda page: _PAGE.dump_json(page).decode(),
        parse=_PAGE.validate_json,
    )


async def _load_page(
    session: AsyncSession,
    *,
    limit: int,
    cursor: dict[str, Any] | None,
    exam_id: uuid.UUID | None,
    search: str | None,
    version_ids: list[uuid.UUID] | None,
    station_ids: list[uuid.UUID] | None,
    all_exams: bool,
) -> tuple[list[LibraryStationRead], str | None]:
    """One page of the library as rows a route returns, read from the database."""
    stations, next_cursor = await repository_library.library_page(
        session,
        limit=limit,
        cursor=cursor,
        exam_id=exam_id,
        search=search,
        version_ids=version_ids,
        station_ids=station_ids,
        # Staff curating the whole catalogue must see a published station before an editor has
        # approved it, same bypass as the plan window above: an unreviewed station still has to
        # be found and fixed by somebody.
        require_approved=not all_exams,
        apply_date_floor=not all_exams,
    )
    version_ids = [
        station.current_version_id for station in stations if station.current_version_id is not None
    ]
    versions = await summaries_by_version_id(session, None, version_ids)
    codes = await catalog.exam_codes_by_id(session, [station.exam_id for station in stations])

    library_reads: list[LibraryStationRead] = []
    for station in stations:
        version = versions.get(station.current_version_id) if station.current_version_id else None
        # A published station with no current version is a seeding fault, not
        # something a browser can act on: there is nothing for it to bind.
        if version is None:
            continue
        library_reads.append(
            LibraryStationRead(
                id=station.id,
                title=station.title,
                exam_code=codes.get(station.exam_id, ""),
                version_id=version.version_id,
                version=version.version,
                published_at=version.published_at,
            )
        )
    return library_reads, next_cursor


async def _offered_by_any(session: AsyncSession, org_ids: Iterable[uuid.UUID], exam_id: uuid.UUID) -> bool:
    """Whether one of these organisations offers the exam (a programme names it)."""
    for org_id in org_ids:
        if exam_id in await catalog.org_exam_ids(session, org_id):
            return True
    return False


async def read_library_station(
    session: AsyncSession,
    station_id: uuid.UUID,
    *,
    user_id: uuid.UUID,
    now: datetime,
    all_exams: bool = False,
) -> LibraryStationRead:
    """One library station, answered for whoever a link found them to be.

    Everything the browse row says and nothing more: the candidate's brief and scenario are disclosed
    by their own attempt once it exists, and the patient's persona and examiner's material never leave
    the server here — a station read from a link is not a station being sat.

    Scoped to the exams the caller may open, same as `browse_library`; `all_exams` is the staff pass.
    """
    found = await repository_library.library_station(
        session, station_id, require_approved=not all_exams, apply_date_floor=not all_exams
    )
    if found is None:
        # One code for "no such station", "not published", and "some
        # institution's own": which of them it was is somebody else's tenant.
        raise errors.StationNotFound()
    station, version = found
    code = await catalog.exam_code_by_id(session, station.exam_id) or ""
    if not all_exams:
        access = await service_access.exam_access_for(session, user_id, now=now)
        if code not in access.codes:
            raise errors.NotEntitled(details={"reason": "no_entitlement"})
        await service_plan_window.ensure_station_in_plan(
            session,
            user_id=user_id,
            station_id=station.id,
            owner_kind=station.owner_kind,
            exam_id=station.exam_id,
            now=now,
        )
    return LibraryStationRead(
        id=station.id,
        title=station.title,
        exam_code=code,
        version_id=version.id,
        version=version.version,
        published_at=version.published_at,
    )


async def library_station_counts(session: AsyncSession, exam_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """How many published library stations each exam has, for a catalogue an institution
    picks from. An exam with no stations yet is absent; read it with a default of zero."""
    return await repository_library.published_counts_by_exam(session, exam_ids)
