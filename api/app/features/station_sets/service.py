"""Practice-set use cases, including the attempt that a set entry starts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, raise_mapped
from app.features.attempts import service as attempts
from app.features.attempts import service_reads as attempts_reads
from app.features.attempts.errors import AttemptNotFinished, AttemptNotReady
from app.features.catalog import service as catalog
from app.features.catalog.service import resolve_exam
from app.features.station_sets import domain, errors, repository
from app.features.station_sets.models import StationSet, StationSetEntry
from app.features.station_sets.schemas import EntryRead, SetRead, StartedAttempt

_REFUSALS: dict[type[Exception], type[AppError]] = {
    domain.AttemptLimitReached: errors.AttemptLimitReachedError,
    domain.SetLocked: errors.SetLockedError,
    domain.NothingToDebrief: errors.NothingToDebriefError,
}


async def create_set(
    session: AsyncSession,
    owner_user_id: uuid.UUID,
    *,
    name: str,
    exam_code: str,
    station_version_ids: list[uuid.UUID],
    now: datetime,
) -> SetRead:
    """Build a practice session out of stations.

    Gated on the same entitlement the attempt is. Without it somebody could
    build a whole session for an exam they do not hold and only be refused at
    the first station — a dead end the client walks them into rather than a
    refusal it can explain.
    """
    exam = await resolve_exam(session, exam_code)
    await attempts.require_entitlement(session, user_id=owner_user_id, exam_id=exam.id, now=now)
    station_set = await repository.create_set(session, owner_user_id, exam_id=exam.id, name=name)
    entries = await repository.add_entries(session, station_set.id, station_version_ids=station_version_ids)
    return _set_read(station_set, exam.code, entries)


async def read_set(session: AsyncSession, owner_user_id: uuid.UUID, set_id: uuid.UUID) -> SetRead:
    station_set = await _require(session, owner_user_id, set_id)
    entries = await repository.entries_for(session, set_id)
    code = await catalog.exam_code_by_id(session, station_set.exam_id)
    return _set_read(station_set, code or "", entries)


async def rename_set(
    session: AsyncSession, owner_user_id: uuid.UUID, set_id: uuid.UUID, *, name: str
) -> SetRead:
    """Change what a set is called.

    Not the station list too: an entry carries the counters for what was sat in it and is what an
    attempt points at, so swapping the list would be deleting somebody's history and numbering a new
    one from zero.
    """
    station_set = await _require(session, owner_user_id, set_id)
    await repository.rename_set(session, station_set, name=name)
    return await read_set(session, owner_user_id, set_id)


async def delete_set(session: AsyncSession, owner_user_id: uuid.UUID, set_id: uuid.UUID) -> None:
    """Throw a set away — as long as nothing was actually sat in it.

    A set with attempts in it is a different object: its entries are what those recordings point at,
    and the schema refuses to take an entry out from under one. This refuses and says what is in the
    way, rather than deleting the recordings to comply; the support console is the route that destroys
    a person's progress, on a stated reason and an audit row.
    """
    await _require(session, owner_user_id, set_id)
    entries = await repository.entries_for(session, set_id)
    sat = await attempts_reads.set_entries_with_attempts(session, [entry.id for entry in entries])
    if sat:
        raise errors.SetHasAttemptsError()
    await repository.delete_set(session, owner_user_id, set_id)


async def list_sets(
    session: AsyncSession, owner_user_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[SetRead], str | None]:
    station_sets, next_cursor = await repository.list_for_owner(
        session, owner_user_id, limit=limit, cursor=cursor
    )
    set_reads = []
    for station_set in station_sets:
        entries = await repository.entries_for(session, station_set.id)
        code = await catalog.exam_code_by_id(session, station_set.exam_id)
        set_reads.append(_set_read(station_set, code or "", entries))
    return set_reads, next_cursor


async def start_entry_attempt(
    session: AsyncSession,
    owner_user_id: uuid.UUID,
    set_id: uuid.UUID,
    entry_id: uuid.UUID,
    *,
    now: datetime,
    debrief: bool = False,
) -> StartedAttempt:
    """Start an attempt at one station in a set.

    The counter moves in the same transaction as the attempt is created, so a limit cannot be
    exceeded by two requests arriving together.
    """
    station_set = await _require(session, owner_user_id, set_id)
    entry = await repository.entry_by_id(session, set_id, entry_id)
    if entry is None:
        raise errors.EntryNotFound()

    exam = await catalog.exam_ref_by_id(session, station_set.exam_id)
    if exam is None:
        raise errors.SetNotFound()

    state = domain.EntryState(attempts=entry.attempts, debrief_attempts=entry.debrief_attempts)
    try:
        if debrief:
            domain.ensure_debriefable(state, limit=exam.station_attempt_limit)
        else:
            domain.ensure_attemptable(state, limit=exam.station_attempt_limit, locked=station_set.locked)
    except Exception as exc:  # noqa: BLE001 - mapped below
        raise_mapped(exc, _REFUSALS)

    if debrief:
        # A debrief is *about* an earlier attempt, and the table requires it to
        # say which. Passing None raised an IntegrityError on every request.
        source_attempt_id = await attempts.latest_attempt_for_set_entry(session, entry.id)
        if source_attempt_id is None:
            raise errors.NothingToDebriefError()
        try:
            attempt = await attempts.start_debrief_attempt(
                session,
                user_id=owner_user_id,
                source_attempt_id=source_attempt_id,
                now=now,
            )
        except (AttemptNotFinished, AttemptNotReady) as exc:
            raise errors.NothingToDebriefError() from exc
    else:
        attempt = await attempts.start_attempt(
            session,
            user_id=owner_user_id,
            kind="set_station",
            exam_code=exam.code,
            now=now,
            station_version_id=entry.station_version_id,
            set_entry_id=entry.id,
        )
    await repository.record_attempt(session, entry.id, at=now, debrief=debrief)

    entries = await repository.entries_for(session, set_id)
    if domain.set_complete(
        [
            domain.EntryState(attempts=set_entry.attempts, debrief_attempts=set_entry.debrief_attempts)
            for set_entry in entries
        ]
    ):
        await repository.mark_complete(session, set_id, at=now)

    used = next((set_entry.attempts for set_entry in entries if set_entry.id == entry.id), entry.attempts + 1)
    return StartedAttempt(
        attempt_id=attempt.id,
        kind=attempt.kind,
        status=attempt.status,
        entry_id=entry.id,
        attempts_used=used,
    )


async def _require(session: AsyncSession, owner_user_id: uuid.UUID, set_id: uuid.UUID) -> StationSet:
    station_set = await repository.set_by_id(session, owner_user_id, set_id)
    if station_set is None:
        raise errors.SetNotFound()
    return station_set


def _set_read(station_set: StationSet, exam_code: str, entries: list[StationSetEntry]) -> SetRead:
    states = [
        domain.EntryState(attempts=entry.attempts, debrief_attempts=entry.debrief_attempts)
        for entry in entries
    ]
    attempted, total = domain.progress(states)
    return SetRead(
        id=station_set.id,
        name=station_set.name,
        exam_code=exam_code,
        locked=station_set.locked,
        completed_at=station_set.completed_at,
        attempted_entries=attempted,
        total_entries=total,
        entries=[
            EntryRead(
                id=entry.id,
                position=entry.position,
                station_version_id=entry.station_version_id,
                attempts=entry.attempts,
                debrief_attempts=entry.debrief_attempts,
                last_attempt_at=entry.last_attempt_at,
            )
            for entry in entries
        ],
    )
