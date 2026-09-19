"""Practice-set use cases, including the attempt that a set entry starts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, raise_mapped
from app.features.attempts import service as attempts
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
    row = await repository.create_set(session, owner_user_id, exam_id=exam.id, name=name)
    entries = await repository.add_entries(session, row.id, station_version_ids=station_version_ids)
    return _set_read(row, exam.code, entries)


async def read_set(session: AsyncSession, owner_user_id: uuid.UUID, set_id: uuid.UUID) -> SetRead:
    row = await _require(session, owner_user_id, set_id)
    entries = await repository.entries_for(session, set_id)
    code = await catalog.exam_code_by_id(session, row.exam_id)
    return _set_read(row, code or "", entries)


async def list_sets(
    session: AsyncSession, owner_user_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[SetRead], str | None]:
    rows, next_cursor = await repository.list_for_owner(session, owner_user_id, limit=limit, cursor=cursor)
    out = []
    for row in rows:
        entries = await repository.entries_for(session, row.id)
        code = await catalog.exam_code_by_id(session, row.exam_id)
        out.append(_set_read(row, code or "", entries))
    return out, next_cursor


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

    The counter moves in the same transaction as the attempt is created, so a
    limit cannot be exceeded by two requests arriving together — which is what
    b2c's read-modify-write on an array allows.
    """
    row = await _require(session, owner_user_id, set_id)
    entry = await repository.entry_by_id(session, set_id, entry_id)
    if entry is None:
        raise errors.EntryNotFound()

    exam = await catalog.exam_ref_by_id(session, row.exam_id)
    if exam is None:
        raise errors.SetNotFound()

    state = domain.EntryState(attempts=entry.attempts, debrief_attempts=entry.debrief_attempts)
    try:
        if debrief:
            domain.ensure_debriefable(state, limit=exam.station_attempt_limit)
        else:
            domain.ensure_attemptable(state, limit=exam.station_attempt_limit, locked=row.locked)
    except Exception as exc:  # noqa: BLE001 - mapped below
        raise_mapped(exc, _REFUSALS)

    source_attempt_id = None
    if debrief:
        # A debrief is *about* an earlier attempt, and the table requires it to
        # say which. Passing None raised an IntegrityError on every request.
        source_attempt_id = await attempts.latest_attempt_for_set_entry(session, entry.id)
        if source_attempt_id is None:
            raise errors.NothingToDebriefError()

    attempt = await attempts.start_attempt(
        session,
        user_id=owner_user_id,
        kind="debrief" if debrief else "set_station",
        exam_code=exam.code,
        now=now,
        station_version_id=entry.station_version_id,
        set_entry_id=None if debrief else entry.id,
        source_attempt_id=source_attempt_id,
    )
    await repository.record_attempt(session, entry.id, at=now, debrief=debrief)

    entries = await repository.entries_for(session, set_id)
    if domain.set_complete(
        [domain.EntryState(attempts=e.attempts, debrief_attempts=e.debrief_attempts) for e in entries]
    ):
        await repository.mark_complete(session, set_id, at=now)

    used = next((e.attempts for e in entries if e.id == entry.id), entry.attempts + 1)
    return StartedAttempt(
        attempt_id=attempt.id,
        kind=attempt.kind,
        status=attempt.status,
        entry_id=entry.id,
        attempts_used=used,
    )


async def _require(session: AsyncSession, owner_user_id: uuid.UUID, set_id: uuid.UUID) -> StationSet:
    row = await repository.set_by_id(session, owner_user_id, set_id)
    if row is None:
        raise errors.SetNotFound()
    return row


def _set_read(row: StationSet, exam_code: str, entries: list[StationSetEntry]) -> SetRead:
    states = [domain.EntryState(attempts=e.attempts, debrief_attempts=e.debrief_attempts) for e in entries]
    attempted, total = domain.progress(states)
    return SetRead(
        id=row.id,
        name=row.name,
        exam_code=exam_code,
        locked=row.locked,
        completed_at=row.completed_at,
        attempted_entries=attempted,
        total_entries=total,
        entries=[
            EntryRead(
                id=e.id,
                position=e.position,
                station_version_id=e.station_version_id,
                attempts=e.attempts,
                debrief_attempts=e.debrief_attempts,
                last_attempt_at=e.last_attempt_at,
            )
            for e in entries
        ],
    )
