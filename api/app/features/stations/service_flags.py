"""What a reader reports about a station, and what staff do about it.

Three use cases: report one, read your own reports, work the staff queue. A flag is a second thing
attached to a station, with its own rules about who may see and change it — not the station's
lifecycle nor a projection of one.
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

    Idempotent, and deliberately so: a double tap of the report button is one report, not a 400.
    The station must exist, but *whose* it is does not matter — a reader in another institution may
    find a case wrong just as easily.
    """
    if not await repository.exists_by_id(session, station_id):
        raise errors.StationNotFound()

    existing = await flags.find(session, station_id=station_id, user_id=user_id)
    flag = existing or await flags.add(session, station_id=station_id, user_id=user_id)
    return _read(flag, None, None)


async def my_reports(session: AsyncSession, user_id: uuid.UUID) -> list[StationFlagRead]:
    """What this person has reported, newest first, with the case's title."""
    reports = await flags.for_reporter(session, user_id)
    return [_read(flag, title, None) for flag, title in reports]


async def queue(
    session: AsyncSession, *, status: str | None, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[StationFlagRead], str | None]:
    """The staff queue: oldest open report first, because that is the one waiting.

    Reports a page at a time and then resolves every name on it in one read each
    of `identity` and of its own stations, rather than once per row.
    """
    page, next_cursor = await flags.list_page(session, status=status, limit=limit, cursor=cursor)
    titles = await flags.titles_by_ids(session, [flag.station_id for flag in page])
    people = await identity.user_refs_by_ids(session, list({flag.user_id for flag in page}))
    reads = [
        _read(
            flag,
            titles.get(flag.station_id),
            people[flag.user_id].name if flag.user_id in people else None,
        )
        for flag in page
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
    flag = await flags.by_id(session, flag_id)
    if flag is None:
        raise errors.StationFlagNotFound()
    return _read(
        await flags.set_resolved(
            session,
            flag,
            status=body.status,
            note=body.note,
            actor_id=actor_id,
            resolved_at=now if body.status == "resolved" else None,
        ),
        (await flags.titles_by_ids(session, [flag.station_id])).get(flag.station_id),
        None,
    )


def _read(flag: StationFlag, station_title: str | None, reporter_name: str | None) -> StationFlagRead:
    """One row to the client, with whatever names the caller resolved for it."""
    return StationFlagRead(
        id=flag.id,
        station_id=flag.station_id,
        station_title=station_title,
        status=flag.status,
        created_at=flag.created_at,
        reporter_name=reporter_name,
        resolution_note=flag.resolution_note,
        resolved_at=flag.resolved_at,
    )
