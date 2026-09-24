"""What a reader reports about a station, and what staff do about it.

Three use cases: report one, read your own reports, work the staff queue. Split
from `service.py` and `service_reads.py` because a flag is neither a station's
lifecycle nor a projection of one — it is a second thing attached to it, with
its own rules about who may see and change it.

The retiring client wrote none of this down: `POST /api/flag_station` appended
`{station_id, mock_id, flagged: true}` to the *user's* Firestore document, so a
report was visible only to the person who made it, the content team never saw
one, and the "Flagged stations" tab was a bookmark list wearing a report's
clothes.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import service as identity
from app.features.stations import errors, repository
from app.features.stations import repository_flags as flags
from app.features.stations.models import StationFlag
from app.features.stations.schemas import StationFlagRead, UpdateStationFlag


async def report(session: AsyncSession, *, station_id: uuid.UUID, user_id: uuid.UUID) -> StationFlagRead:
    """Say this station is wrong.

    Idempotent, and deliberately so: the button is one tap in a station header,
    a double tap is one report, and the legacy answer to a repeat was 400
    "Station is already flagged" — which the client surfaced as "we couldn't
    flag this station" over a report that had in fact been recorded.

    The station must exist, but *whose* it is does not matter: a reader inside
    somebody else's institution may find a case wrong just as easily, and
    refusing them loses the report.
    """
    if not await repository.exists_by_id(session, station_id):
        raise errors.StationNotFound()

    existing = await flags.find(session, station_id=station_id, user_id=user_id)
    row = existing or await flags.add(session, station_id=station_id, user_id=user_id)
    return _read(row, None, None)


async def my_reports(session: AsyncSession, user_id: uuid.UUID) -> list[StationFlagRead]:
    """What this person has reported, newest first, with the case's title."""
    rows = await flags.for_reporter(session, user_id)
    return [_read(row, title, None) for row, title in rows]


async def queue(
    session: AsyncSession, *, status: str | None, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[StationFlagRead], str | None]:
    """The staff queue: oldest open report first, because that is the one waiting.

    Reports a page at a time and then resolves every name on it in one read each
    of `identity` and of its own stations, rather than once per row.
    """
    rows, next_cursor = await flags.list_page(session, status=status, limit=limit, cursor=cursor)
    titles = await flags.titles_by_ids(session, [row.station_id for row in rows])
    people = await identity.user_refs_by_ids(session, list({row.user_id for row in rows}))
    reads = [
        _read(
            row,
            titles.get(row.station_id),
            people[row.user_id].name if row.user_id in people else None,
        )
        for row in rows
    ]
    return reads, next_cursor


async def decide(
    session: AsyncSession,
    flag_id: uuid.UUID,
    *,
    body: UpdateStationFlag,
    actor_id: uuid.UUID,
    now: datetime,
) -> StationFlagRead:
    """Close a report, or put it back on the queue.

    `resolved_at` is cleared on reopen rather than left to read as history: a
    row that says `open` and carries a resolution timestamp answers to nobody.
    """
    row = await flags.by_id(session, flag_id)
    if row is None:
        raise errors.StationFlagNotFound()
    return _read(
        await flags.set_resolved(
            session,
            row,
            status=body.status,
            note=body.note,
            actor_id=actor_id,
            resolved_at=now if body.status == "resolved" else None,
        ),
        (await flags.titles_by_ids(session, [row.station_id])).get(row.station_id),
        None,
    )


def _read(row: StationFlag, station_title: str | None, reporter_name: str | None) -> StationFlagRead:
    """One row to the client, with whatever names the caller resolved for it."""
    return StationFlagRead(
        id=row.id,
        station_id=row.station_id,
        station_title=station_title,
        status=row.status,
        created_at=row.created_at,
        reporter_name=reporter_name,
        resolution_note=row.resolution_note,
        resolved_at=row.resolved_at,
    )
