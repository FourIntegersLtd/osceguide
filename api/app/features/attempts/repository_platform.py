"""Storage reads and the one write the platform console asks about a person's attempts as a whole.

`repository.list_for_user` pages one person's attempts; these answer across people (the directory's
facets) and across a person's stations (the progress screen), and carry the only delete this table
has — the console's "delete station progress".
"""

from __future__ import annotations

import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.domain import Status
from app.features.attempts.models import Attempt


async def attempted_user_ids(session: AsyncSession) -> set[uuid.UUID]:
    """Everyone who has ever started anything — the "trial" facet's other half."""
    stmt = select(Attempt.user_id).distinct()
    return set((await session.execute(stmt)).scalars())


async def count_by_user(session: AsyncSession, user_ids: Collection[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not user_ids:
        return {}
    stmt = (
        select(Attempt.user_id, func.count(Attempt.id))
        .where(Attempt.user_id.in_(list(user_ids)))
        .group_by(Attempt.user_id)
    )
    return {user_id: int(n) for user_id, n in (await session.execute(stmt)).all()}


@dataclass(frozen=True)
class VersionProgress:
    """One person's attempts at one station version, summed up."""

    station_version_id: uuid.UUID
    attempts: int
    evaluated: int
    last_attempt_at: datetime
    last_attempt_id: uuid.UUID
    last_status: str


async def progress_by_version(session: AsyncSession, user_id: uuid.UUID) -> list[VersionProgress]:
    """This person's attempts grouped by station version, newest station first.

    Debriefs are attempts *about* an earlier attempt and are left out: they
    would count a station as sat when the person only talked it through.

    Two queries rather than one: the newest attempt per version is picked
    with `DISTINCT ON` ordered by `(created_at, id)`, because attempts
    written in one transaction share a `created_at` and a join on the
    maximum timestamp would return all of them.
    """
    sat = (Attempt.user_id == user_id, Attempt.station_version_id.is_not(None), Attempt.kind != "debrief")
    counts = (
        select(
            Attempt.station_version_id,
            func.count(Attempt.id),
            func.count(Attempt.id).filter(Attempt.status == str(Status.EVALUATED)),
        )
        .where(*sat)
        .group_by(Attempt.station_version_id)
    )
    totals = {
        version_id: (int(attempts), int(evaluated))
        for version_id, attempts, evaluated in (await session.execute(counts)).all()
    }
    newest = (
        select(Attempt.station_version_id, Attempt.id, Attempt.status, Attempt.created_at)
        .where(*sat)
        .distinct(Attempt.station_version_id)
        .order_by(Attempt.station_version_id, Attempt.created_at.desc(), Attempt.id.desc())
    )
    rows = [
        VersionProgress(
            station_version_id=version_id,
            attempts=totals[version_id][0],
            evaluated=totals[version_id][1],
            last_attempt_at=created_at,
            last_attempt_id=attempt_id,
            last_status=status,
        )
        for version_id, attempt_id, status, created_at in (await session.execute(newest)).all()
    ]
    return sorted(rows, key=lambda row: (row.last_attempt_at, row.last_attempt_id), reverse=True)


async def running_for_user_versions(
    session: AsyncSession, user_id: uuid.UUID, version_ids: Collection[uuid.UUID]
) -> int:
    """How many of this person's attempts at these versions are mid-consultation."""
    if not version_ids:
        return 0
    stmt = select(func.count(Attempt.id)).where(
        Attempt.user_id == user_id,
        Attempt.station_version_id.in_(list(version_ids)),
        Attempt.status == str(Status.RUNNING),
    )
    return int((await session.execute(stmt)).scalar_one())


async def delete_for_user_versions(
    session: AsyncSession, user_id: uuid.UUID, version_ids: Collection[uuid.UUID]
) -> int:
    """Remove every attempt this person made at these versions — and, through
    the foreign keys, its turns, transcript, results and debrief summary.
    Debriefs *about* one of them go too, being attempts at the same version;
    an attempt elsewhere that named one as its source keeps a null pointer.
    """
    if not version_ids:
        return 0
    result = await session.execute(
        delete(Attempt).where(Attempt.user_id == user_id, Attempt.station_version_id.in_(list(version_ids)))
    )
    return int(getattr(result, "rowcount", 0) or 0)
