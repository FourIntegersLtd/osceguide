"""Reading the platform library: the browse page, and one station from it.

Split from `service_reads.py` by what is being answered for. That module answers
about stations for a caller that already holds ids; this one is the library's
own reader — the screen that lists it and the deep link that names one station.
Both halves keep the slice's rule about the library: a row is a title and the
ids needed to bind it, never the document inside it. A link is still browsing,
and browsing is not reading the answers.

`read_library_station` retires a walk. Without a per-station read the new
client fetched the browse pages in sequence — up to twenty of them — to answer
"what is this station?", which is a title lookup implemented as a catalogue
download and stops working the day the library outgrows the walk.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import service as catalog
from app.features.entitlements import service_access
from app.features.stations import errors, repository_library
from app.features.stations.schemas import LibraryStationRead
from app.features.stations.service_reads import summaries_by_version_id


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
) -> tuple[list[LibraryStationRead], str | None]:
    """The published platform library, scoped to the exams the caller may open.

    The `owner_kind = 'platform'` half of the table had no reader at all: a
    consumer could build a practice set only out of station version ids they
    had no way to discover. An unpublished station is not in the library, and
    neither is any organisation's own — those are behind the org routes.

    It answered with every exam's stations at once, which is what put an "all
    exams" filter on a screen in a product where somebody holds one exam. A
    named `exam_code` must be one the caller may open; without one they get
    theirs. `all_exams` is the staff console, which curates the whole
    catalogue and passes it explicitly rather than by omission.

    `search` is a fragment of a title, answered in SQL. It used to be typed
    into a browser that could only match the pages it had already pulled down,
    which made "no results" mean "not on the first two thousand".
    """
    exam_id = None
    if exam_code is not None:
        if user_id is not None and now is not None and not all_exams:
            await service_access.require_exam_access(session, user_id, exam_code=exam_code, now=now)
        exam_id = (await catalog.resolve_exam(session, exam_code)).id
    elif user_id is not None and now is not None and not all_exams:
        # No exam named: theirs, rather than everybody's.
        access = await service_access.exam_access_for(session, user_id, now=now)
        if access.current is None:
            # Nothing they may open, so nothing to browse. An empty page rather than
            # a refusal: a brand-new account with no exam chosen has no library yet.
            return [], None
        exam_id = (await catalog.resolve_exam(session, access.current)).id

    rows, next_cursor = await repository_library.library_page(
        session, limit=limit, cursor=cursor, exam_id=exam_id, search=search
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


async def read_library_station(
    session: AsyncSession,
    station_id: uuid.UUID,
    *,
    user_id: uuid.UUID,
    now: datetime,
    all_exams: bool = False,
) -> LibraryStationRead:
    """One library station, answered for whoever a link found them to be.

    Everything the browse row says and nothing more, so the route cannot
    disclose what a station holds: the candidate's brief and the scenario are
    disclosed by their own attempt, once it exists, and the patient's persona
    and the examiner's material never leave the server (`domain_content.py` is
    that projection, and it is deliberately not applied here — a station read
    from a link is not a station being sat).

    The library is scoped to the exams a caller may open, and a station whose
    exam they cannot open is not in *their* library. `all_exams` is the same
    staff pass the browse route takes: curating the catalogue means reading
    across every exam in it.
    """
    found = await repository_library.library_station(session, station_id)
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
    return LibraryStationRead(
        id=station.id,
        title=station.title,
        exam_code=code,
        version_id=version.id,
        version=version.version,
        published_at=version.published_at,
    )
