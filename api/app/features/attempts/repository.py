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
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.attempts.domain import Status
from app.features.attempts.models import Attempt, AttemptLiveCoverage


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
    """Insert one new attempt row and return it, id and timestamps filled in."""
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

    Typed as the enum, not `str`: a bare string once let `"runnning"` through as a write the database
    accepted and nothing would ever match again. The column now carries a CHECK too.
    """
    updates: dict[str, Any] = {"status": str(status)}
    if status is Status.RUNNING:
        updates["started_at"] = at
    elif status is Status.INTERACTION_COMPLETE:
        updates["completed_at"] = at
    elif status is Status.FAILED:
        updates["failed_reason"] = reason
    await session.execute(update(Attempt).where(Attempt.id == attempt_id).values(**updates))


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
    """Which of these practice-set entries has at least one attempt against it."""
    if not entry_ids:
        return set()
    stmt = select(Attempt.set_entry_id).where(Attempt.set_entry_id.in_(list(entry_ids))).distinct()
    return {entry_id for entry_id in (await session.execute(stmt)).scalars() if entry_id is not None}


async def latest_status_by_set_entry(
    session: AsyncSession, entry_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, str]:
    """The status of the most recently created attempt against each of these set entries.

    One query for every entry a set holds, not one per entry: `DISTINCT ON` asks
    Postgres to keep only the newest row per `set_entry_id`, ordered by when the
    attempt was created (ties broken by id so the answer is stable). This is what
    `station_sets` reads to decide whether a set has a "Feedback" badge to show —
    an entry whose latest attempt has not reached `evaluated` is not ready yet,
    even if an earlier attempt at the same station was.
    """
    if not entry_ids:
        return {}
    stmt = (
        select(Attempt.set_entry_id, Attempt.status)
        .where(Attempt.set_entry_id.in_(list(entry_ids)))
        .distinct(Attempt.set_entry_id)
        .order_by(Attempt.set_entry_id, Attempt.created_at.desc(), Attempt.id.desc())
    )
    return {
        entry_id: status for entry_id, status in (await session.execute(stmt)).all() if entry_id is not None
    }


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
    """This person's attempts, newest first, optionally narrowed to one station, set entry or status."""
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

    Counted per exam, not per account: b2c held a person as four separate documents, one per product,
    each with its own trial, so somebody who used their SCA trial still had a PLAB one.
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
    """The exam a station belongs to, read through its version — a raw join for a hot path."""
    stmt = text(
        "SELECT s.exam_id FROM station_versions v "
        "JOIN stations s ON s.id = v.station_id WHERE v.id = :version_id"
    )
    return (await session.execute(stmt, {"version_id": station_version_id})).scalar_one_or_none()


async def evaluated_for_user(
    session: AsyncSession, user_id: uuid.UUID, *, exam_id: uuid.UUID | None = None, limit: int
) -> list[Attempt]:
    """This person's marked attempts, newest first, optionally for one exam.

    Filtered in SQL rather than by reading a page of everything and discarding the unmarked rows:
    somebody who practises daily has hundreds of attempts.
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
    """How many attempts have been marked — the feedback counter shown on the landing page."""
    stmt = select(func.count()).select_from(Attempt).where(Attempt.status == str(Status.EVALUATED))
    return int((await session.execute(stmt)).scalar_one())


# --- Live coverage snapshots.


async def read(session: AsyncSession, attempt_id: uuid.UUID) -> dict[str, Any] | None:
    """This attempt's live coverage snapshot, or `None` if nothing has been computed yet."""
    coverage = await session.get(AttemptLiveCoverage, attempt_id)
    return coverage.snapshot if coverage else None


async def save(session: AsyncSession, attempt_id: uuid.UUID, snapshot: dict[str, Any]) -> None:
    """Overwrite this attempt's coverage snapshot, creating the row on the first write."""
    stmt = insert(AttemptLiveCoverage).values(attempt_id=attempt_id, snapshot=snapshot)
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=[AttemptLiveCoverage.attempt_id],
            set_={"snapshot": stmt.excluded.snapshot},
        )
    )


# --- Source consultations for a learner's debrief summaries.


async def sources_for(
    session: AsyncSession,
    user_id: uuid.UUID,
    attempt_ids: list[uuid.UUID],
) -> dict[uuid.UUID, uuid.UUID]:
    """Map each of these debrief attempts to the id of the consultation it is about."""
    debrief_sources = await session.execute(
        select(Attempt.id, Attempt.source_attempt_id).where(
            Attempt.user_id == user_id,
            Attempt.id.in_(attempt_ids),
            Attempt.kind == "debrief",
            Attempt.source_attempt_id.is_not(None),
        )
    )
    return {attempt_id: source_id for attempt_id, source_id in debrief_sources.all() if source_id is not None}


# --- The attempt rows that belong to an exam slot.


async def live_attempts_for_slots(session: AsyncSession, slot_ids: Sequence[uuid.UUID]) -> list[Attempt]:
    """The one unfailed attempt on each of these slots, for a screen that lists them."""
    if not slot_ids:
        return []
    stmt = select(Attempt).where(Attempt.slot_id.in_(list(slot_ids)), Attempt.status != "failed")
    return list((await session.execute(stmt)).scalars())


async def live_attempt_for_slot(session: AsyncSession, slot_id: uuid.UUID) -> Attempt | None:
    """The one unfailed attempt currently on this slot, if any."""
    stmt = select(Attempt).where(Attempt.slot_id == slot_id, Attempt.status != "failed")
    return (await session.execute(stmt)).scalar_one_or_none()


async def fail_live_attempt_for_slot(
    session: AsyncSession, slot_id: uuid.UUID, *, at: datetime, reason: str
) -> None:
    """Fail whatever is still live on this slot, and make it visible.

    Flushed here because the insert that follows has to see it: the partial
    unique index on `(slot_id) where status <> 'failed'` would otherwise refuse
    the new attempt.
    """
    live = await live_attempt_for_slot(session, slot_id)
    if live is None:
        return
    await set_status(session, live.id, status=Status.FAILED, at=at, reason=reason)
    await session.flush()


async def exam_for_slot_attempt(session: AsyncSession, slot_id: uuid.UUID) -> uuid.UUID | None:
    """The exam a previous attempt on this slot ran under.

    Reused on re-dispatch so a retry is marked against the same framework as
    the recording it replaces.
    """
    stmt = (
        select(Attempt.exam_id).where(Attempt.slot_id == slot_id).order_by(Attempt.created_at.desc()).limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def slots_with_attempts(session: AsyncSession, slot_ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
    """Which of these exam slots has at least one attempt against it."""
    if not slot_ids:
        return set()
    stmt = select(Attempt.slot_id).where(Attempt.slot_id.in_(list(slot_ids))).distinct()
    return {slot_id for slot_id in (await session.execute(stmt)).scalars() if slot_id is not None}
