"""Storage for attempts, their turns and their results.

Attempts are not org-scoped in the usual way: a consumer attempt has no
organisation at all. The org-scoped reads say so in their names, and the
worker-facing reads take an attempt id because that is all a worker is given.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.attempts.domain import Status
from app.features.attempts.models import Attempt


async def create_attempt(
    session: AsyncSession,
    *,
    kind: str,
    user_id: uuid.UUID,
    exam_id: uuid.UUID,
    org_id: uuid.UUID | None = None,
    station_version_id: uuid.UUID | None = None,
    slot_id: uuid.UUID | None = None,
    set_entry_id: uuid.UUID | None = None,
    peer_session_id: uuid.UUID | None = None,
    source_attempt_id: uuid.UUID | None = None,
    room_name: str | None = None,
) -> Attempt:
    attempt = Attempt(
        kind=kind,
        user_id=user_id,
        exam_id=exam_id,
        org_id=org_id,
        station_version_id=station_version_id,
        slot_id=slot_id,
        set_entry_id=set_entry_id,
        peer_session_id=peer_session_id,
        source_attempt_id=source_attempt_id,
        room_name=room_name,
    )
    session.add(attempt)
    await session.flush()
    await session.refresh(attempt)
    return attempt


async def attempt_by_id(session: AsyncSession, attempt_id: uuid.UUID) -> Attempt | None:
    return (await session.execute(select(Attempt).where(Attempt.id == attempt_id))).scalar_one_or_none()


async def set_status(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    status: Status,
    at: datetime,
    reason: str | None = None,
) -> None:
    """Move an attempt's status.

    Typed as the enum, not `str`: this took a bare string, so `"runnning"` was
    a write the database accepted and nothing would ever match again. The
    column now carries a CHECK as well, which is the belt to this brace.
    """
    values: dict[str, Any] = {"status": str(status)}
    if status is Status.RUNNING:
        values["started_at"] = at
    elif status is Status.INTERACTION_COMPLETE:
        values["completed_at"] = at
    elif status is Status.FAILED:
        values["failed_reason"] = reason
    await session.execute(update(Attempt).where(Attempt.id == attempt_id).values(**values))


async def freeze_definition(
    session: AsyncSession, attempt_id: uuid.UUID, *, definition: dict[str, Any], at: datetime
) -> None:
    """Write the rendered definition once.

    Guarded on `definition IS NULL` in the statement itself rather than by a
    read-then-write, so two workers racing to bootstrap the same attempt cannot
    both believe they were first.
    """
    await session.execute(
        update(Attempt)
        .where(Attempt.id == attempt_id, Attempt.definition.is_(None))
        .values(definition=definition, definition_frozen_at=at)
    )


async def latest_for_set_entry(session: AsyncSession, set_entry_id: uuid.UUID) -> Attempt | None:
    """The most recent attempt at one station of a practice set."""
    stmt = (
        select(Attempt)
        .where(Attempt.set_entry_id == set_entry_id)
        .order_by(Attempt.created_at.desc(), Attempt.id.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def set_entries_with_attempts(session: AsyncSession, entry_ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
    if not entry_ids:
        return set()
    stmt = select(Attempt.set_entry_id).where(Attempt.set_entry_id.in_(list(entry_ids))).distinct()
    return {row for row in (await session.execute(stmt)).scalars() if row is not None}


async def list_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    station_version_id: uuid.UUID | None = None,
    set_entry_id: uuid.UUID | None = None,
    status: Status | None = None,
) -> tuple[list[Attempt], str | None]:
    """This person's attempts, newest first, optionally narrowed to one station.

    The filters are what the screens listing attempts ask: every attempt at one
    station, every attempt at one entry of a practice set, and — for the
    support console — every attempt stuck in one status.
    """
    stmt = select(Attempt).where(Attempt.user_id == user_id)
    if station_version_id is not None:
        stmt = stmt.where(Attempt.station_version_id == station_version_id)
    if set_entry_id is not None:
        stmt = stmt.where(Attempt.set_entry_id == set_entry_id)
    if status is not None:
        stmt = stmt.where(Attempt.status == str(status))
    return await keyset_page(
        session, stmt, sort_col=Attempt.created_at, id_col=Attempt.id, limit=limit, cursor=cursor
    )


async def trial_counts(session: AsyncSession, user_id: uuid.UUID, exam_id: uuid.UUID) -> tuple[int, int]:
    """`(set stations used, attempts completed)` for the free-trial rule.

    Counted per exam, not per account. b2c held a person as four separate user
    documents, one per product, each with its own trial — so somebody who used
    their SCA trial still had a PLAB one. Counting across the unified account
    would quietly take that away from everybody mid-migration.
    """
    set_stations = await session.scalar(
        select(func.count())
        .select_from(Attempt)
        .where(
            Attempt.user_id == user_id,
            Attempt.exam_id == exam_id,
            Attempt.kind == "set_station",
        )
    )
    completed = await session.scalar(
        select(func.count())
        .select_from(Attempt)
        .where(
            Attempt.user_id == user_id,
            Attempt.exam_id == exam_id,
            Attempt.status.in_(("interaction_complete", "evaluated")),
        )
    )
    return int(set_stations or 0), int(completed or 0)


async def exam_for_station_version(session: AsyncSession, station_version_id: uuid.UUID) -> uuid.UUID | None:
    """The exam a station belongs to, read through its version.

    A join rather than a cross-slice call: `attempts` sits above `stations` and
    needs one column of it on a hot path.
    """
    stmt = text(
        "SELECT s.exam_id FROM station_versions v "
        "JOIN stations s ON s.id = v.station_id WHERE v.id = :version_id"
    )
    return (await session.execute(stmt, {"version_id": station_version_id})).scalar_one_or_none()


async def evaluated_for_user(
    session: AsyncSession, user_id: uuid.UUID, *, exam_id: uuid.UUID | None = None, limit: int
) -> list[Attempt]:
    """This person's marked attempts, newest first, optionally for one exam.

    Filtered in SQL rather than by reading a page of everything and discarding
    the unmarked rows: somebody who practises daily has hundreds of attempts
    and the marked ones are what a performance chart is drawn from.
    """
    stmt = select(Attempt).where(Attempt.user_id == user_id, Attempt.status == Status.EVALUATED)
    if exam_id is not None:
        stmt = stmt.where(Attempt.exam_id == exam_id)
    stmt = stmt.order_by(Attempt.created_at.desc(), Attempt.id.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars())


# What "has happened" means for the public counters: the consultation ran to
# the end, whether or not the marking has caught up with it.
_COMPLETED = (Status.INTERACTION_COMPLETE, Status.EVALUATED)


async def count_completed(session: AsyncSession, *, kind: str | None = None) -> int:
    """How many consultations have actually happened.

    `kind` narrows it — `debrief` for the debriefs, nothing for everything
    else. Counted rather than paged: the caller wants the number.
    """
    stmt = select(func.count()).select_from(Attempt).where(Attempt.status.in_(_COMPLETED))
    stmt = stmt.where(Attempt.kind == kind) if kind else stmt.where(Attempt.kind != "debrief")
    return int((await session.execute(stmt)).scalar_one())


async def count_evaluated(session: AsyncSession) -> int:
    """How many attempts have been marked — the feedback counter.

    An evaluated attempt has a result the candidate can read. The landing-page
    statistics band shows this as the feedback number; legacy logs had it
    within 0.5%% of consultations, so it is the same population once marking
    has caught up.
    """
    stmt = select(func.count()).select_from(Attempt).where(Attempt.status == str(Status.EVALUATED))
    return int((await session.execute(stmt)).scalar_one())
