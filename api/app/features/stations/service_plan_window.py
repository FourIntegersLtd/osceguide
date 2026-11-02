"""Which platform-library stations a person's plan lets them see and start.

A plan limit (`billing.service_station_limit`) only ever applies to `owner_kind == "platform"`
stations: an institution's own stations, a marketplace listing, and a learner's own creation are
never capped by anything sold here. Everything in this module answers "all of them" (`None`)
the moment there is nothing to cap, so a deployment with no plan limits set behaves exactly as
it did before this module existed.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import service_reads as attempts_reads
from app.features.billing import service_station_limit
from app.features.stations import errors, repository_library


async def _used_station_ids(
    session: AsyncSession, *, user_id: uuid.UUID, exam_id: uuid.UUID
) -> set[uuid.UUID]:
    """The library stations behind every version this person has sat for the exam.

    `used_station_version_ids` hands back version ids, because the attempts slice does not
    import the stations slice's `models`; this resolves each version to its station with the
    stations slice's own repository instead of reaching into attempts' storage.
    """
    version_ids = await attempts_reads.used_station_version_ids(session, user_id=user_id, exam_id=exam_id)
    if not version_ids:
        return set()
    pairs = await repository_library.versions_with_stations(session, None, list(version_ids))
    return {station.id for _version, station in pairs if station.owner_kind == "platform"}


async def plan_usage(
    session: AsyncSession, *, user_id: uuid.UUID, exam_id: uuid.UUID, exam_code: str, now: datetime
) -> tuple[int, int | None]:
    """How many library stations this person has sat for the exam, and their plan's total limit.

    The limit is `None` when no cap applies. The numbers the setup screen's progress bar reads, so
    "sat of limit" comes from the same rule that decides which stations are open.
    """
    limit = await service_station_limit.station_limit_for(
        session, user_id=user_id, exam_id=exam_id, exam_code=exam_code, now=now
    )
    used_ids = await _used_station_ids(session, user_id=user_id, exam_id=exam_id)
    return len(used_ids), limit


async def allowed_station_ids(
    session: AsyncSession, *, user_id: uuid.UUID, exam_id: uuid.UUID, exam_code: str, now: datetime
) -> set[uuid.UUID] | None:
    """The platform-library stations this person may see and start for the exam.

    `None` means no limit applies: every published, in-window station is allowed. Otherwise the
    plan's limit is the person's total: every station already sat stays open (to retry), and the
    earliest stations not yet sat are added until the total reaches the limit. Someone who has sat
    40 of 53 can start 13 more; someone at or past the limit can only revisit what they sat.
    """
    limit = await service_station_limit.station_limit_for(
        session, user_id=user_id, exam_id=exam_id, exam_code=exam_code, now=now
    )
    if limit is None:
        return None
    used_ids = await _used_station_ids(session, user_id=user_id, exam_id=exam_id)
    new_ids = await repository_library.first_station_ids(
        session, exam_id=exam_id, limit=limit - len(used_ids), exclude_ids=used_ids
    )
    return used_ids | set(new_ids)


async def ensure_station_in_plan(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    station_id: uuid.UUID,
    owner_kind: str,
    exam_id: uuid.UUID,
    now: datetime,
) -> None:
    """Refuse a platform-library station that falls outside the person's plan window.

    Scalar fields rather than a `Station` row: `attempts` calls this too, and a slice may only
    cross-import another slice's `service*`, never its `models`. A no-op for any station this
    slice does not cap (not `owner_kind == "platform"`) and for anyone whose plan carries no
    limit: `allowed_station_ids` returning `None` means everything is in view, so there is
    nothing here to check against.
    """
    if owner_kind != "platform":
        return
    from app.features.catalog.service import exam_code_by_id  # import cycle

    exam_code = await exam_code_by_id(session, exam_id)
    if exam_code is None:
        # The exam a published station belongs to cannot vanish (a RESTRICT foreign key), but
        # nothing here is worth crashing a read over if it somehow did.
        return
    allowed = await allowed_station_ids(
        session, user_id=user_id, exam_id=exam_id, exam_code=exam_code, now=now
    )
    if allowed is not None and station_id not in allowed:
        raise errors.StationNotInPlan()
