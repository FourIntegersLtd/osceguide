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
from app.features.entitlements import service as entitlements
from app.features.station_sets import domain, errors, repository
from app.features.station_sets.models import StationSet, StationSetEntry
from app.features.station_sets.schemas import (
    EntryRead,
    FlaggedEntryRead,
    SetAllowance,
    SetRead,
    StartedAttempt,
)
from app.features.stations import service_reads as stations_reads

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
    await _ensure_within_trial(session, owner_user_id, exam.id, station_version_ids, now=now)
    station_set = await repository.create_set(session, owner_user_id, exam_id=exam.id, name=name)
    entries = await repository.add_entries(session, station_set.id, station_version_ids=station_version_ids)
    return await _set_read(session, station_set, exam.code, entries)


async def allowance(
    session: AsyncSession, owner_user_id: uuid.UUID, *, exam_code: str, now: datetime
) -> SetAllowance:
    """How many new stations a session for this exam may hold, so the setup screen caps its picker."""
    exam = await resolve_exam(session, exam_code)
    return SetAllowance(
        free_stations_left=await _free_stations_left(session, owner_user_id, exam.id, now=now)
    )


async def _free_stations_left(
    session: AsyncSession, owner_user_id: uuid.UUID, exam_id: uuid.UUID, *, now: datetime
) -> int | None:
    """How many more stations a free-trial learner may add, or None when they have paid access."""
    trial = await attempts.trial_state_for(session, user_id=owner_user_id, exam_id=exam_id)
    return await entitlements.free_stations_left(
        session, user_id=owner_user_id, exam_id=exam_id, now=now, trial=trial
    )


async def _ensure_within_trial(
    session: AsyncSession,
    owner_user_id: uuid.UUID,
    exam_id: uuid.UUID,
    station_version_ids: list[uuid.UUID],
    *,
    now: datetime,
) -> None:
    """Refuse a free-trial set that needs more new stations than the trial has left.

    Counted by station, not version, as the trial counts. A station already sat in any of this
    person's sets costs nothing more, so editing a set around it is never refused for it.
    """
    stations_left = await _free_stations_left(session, owner_user_id, exam_id, now=now)
    if stations_left is None:
        return
    sat = await repository.sat_version_ids(session, owner_user_id, exam_id)
    stations = await stations_reads.stations_by_version_id(session, [*station_version_ids, *sat])

    def station_of(version_id: uuid.UUID) -> uuid.UUID:
        """The station a version belongs to, so two versions of one case count once."""
        found = stations.get(version_id)
        return found.station_id if found is not None else version_id

    requested = {station_of(version_id) for version_id in station_version_ids}
    new_stations = requested - {station_of(version_id) for version_id in sat}
    if len(new_stations) > stations_left:
        raise errors.TrialStationLimitError(details={"stations_left": stations_left})


async def read_set(session: AsyncSession, owner_user_id: uuid.UUID, set_id: uuid.UUID) -> SetRead:
    """One of this person's own practice sets, with its stations and progress."""
    station_set = await _require(session, owner_user_id, set_id)
    entries = await repository.entries_for(session, set_id)
    code = await catalog.exam_code_by_id(session, station_set.exam_id)
    return await _set_read(session, station_set, code or "", entries)


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


async def replace_entries(
    session: AsyncSession,
    owner_user_id: uuid.UUID,
    set_id: uuid.UUID,
    *,
    station_version_ids: list[uuid.UUID],
    now: datetime,
) -> SetRead:
    """Swap a set's stations for a different list, in this order — the legacy "edit session" screen.

    A version that stays in the list keeps its existing entry, counters and all: an entry is what an
    attempt points at, so a station left in place must not look, to the candidate, like a station they
    have never sat. Matching is by position among equal version ids (a "bucket pop"), not by first
    occurrence only, so asking for the same station twice keeps both of its existing entries rather
    than treating the second as brand new.

    A version dropped from the list is only actually removed if nothing has been attempted at it yet;
    one that has is left in place and reported as `EntryHasAttemptsError`, naming what is in the way,
    the same shape `delete_set` already uses for a whole set that cannot be thrown away.

    Refuses outright, before touching anything, if the set is locked (access lapsed — nothing about it
    may change) or if any requested version does not exist, was never published, or belongs to a
    station filed under a different exam than this set's own: legacy's edit screen had no minimum or
    maximum station count, so none is enforced here either.
    """
    station_set = await _require(session, owner_user_id, set_id)
    if station_set.locked:
        raise errors.SetLockedError()

    if station_version_ids:
        summaries = await stations_reads.summaries_by_version_id(session, None, station_version_ids)
        for version_id in station_version_ids:
            summary = summaries.get(version_id)
            if summary is None or summary.status != "published" or summary.exam_id != station_set.exam_id:
                raise errors.StationVersionNotUsableError()
    await _ensure_within_trial(session, owner_user_id, station_set.exam_id, station_version_ids, now=now)

    existing_entries = await repository.entries_for(session, set_id)
    # Bucket the existing entries by the version they point at, in the order they
    # were added, so each requested version id can "pop" its earliest surviving
    # match rather than always grabbing the first entry that was ever created
    # for it — the difference matters only when a version appears more than once.
    entries_by_version: dict[uuid.UUID, list[StationSetEntry]] = {}
    for entry in existing_entries:
        entries_by_version.setdefault(entry.station_version_id, []).append(entry)

    # Walk the request once, popping each version's earliest surviving entry as it is
    # claimed. `None` in `final_order` is a placeholder for "a new entry goes here",
    # filled in once `add_entries` hands back the ids it created for `new_version_ids_in_order`.
    kept_entry_ids_in_order: list[uuid.UUID] = []
    new_version_ids_in_order: list[uuid.UUID] = []
    final_order: list[uuid.UUID | None] = []
    for version_id in station_version_ids:
        bucket = entries_by_version.get(version_id)
        if bucket:
            entry_id = bucket.pop(0).id
            kept_entry_ids_in_order.append(entry_id)
            final_order.append(entry_id)
        else:
            new_version_ids_in_order.append(version_id)
            final_order.append(None)

    # Whatever is left in every bucket after that popping is a station the new
    # list does not ask for at all, and is the set of entries to consider removing.
    removed_entry_ids = [entry.id for bucket in entries_by_version.values() for entry in bucket]
    sat_entry_ids = await attempts_reads.set_entries_with_attempts(session, removed_entry_ids)
    if sat_entry_ids:
        raise errors.EntryHasAttemptsError()

    # Park the surviving entries out of the way of the positions `0..n` before either
    # deleting the ones going away or inserting the ones that are new: both of the
    # next two steps would otherwise collide with the unique `(set_id, position)`.
    await repository.park_entries(session, kept_entry_ids_in_order)
    if removed_entry_ids:
        await repository.delete_entries(session, set_id, removed_entry_ids)
    new_entries = await repository.add_entries(session, set_id, station_version_ids=new_version_ids_in_order)
    new_entry_ids = iter(entry.id for entry in new_entries)
    resolved_order = [entry_id if entry_id is not None else next(new_entry_ids) for entry_id in final_order]

    await repository.reposition_entries(session, resolved_order)
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
    """This person's practice sets, each with its own stations and progress."""
    station_sets, next_cursor = await repository.list_for_owner(
        session, owner_user_id, limit=limit, cursor=cursor
    )
    set_reads = []
    for station_set in station_sets:
        entries = await repository.entries_for(session, station_set.id)
        code = await catalog.exam_code_by_id(session, station_set.exam_id)
        set_reads.append(await _set_read(session, station_set, code or "", entries))
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
    """Open a station in a set, creating the attempt the candidate brief is read through.

    This only creates the attempt row, at status `created`. It does *not* count against the
    entry's limit: `record_started_attempt` does that, once the candidate actually starts the
    consultation. A candidate who opens the station and leaves — never pressing "start" — must not
    spend a go they never had; the limit check below is only a fast, best-effort refusal so an
    exhausted entry says no immediately rather than opening a room the candidate cannot use, and the
    counter it reads (`entry.attempts`) already counts only started attempts, never merely-opened
    ones.
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
    # Not counted here: the attempt exists but has not been sat, so the entry's counter — and
    # therefore whether the set is complete — is unchanged until `record_started_attempt` runs.
    return StartedAttempt(
        attempt_id=attempt.id,
        kind=attempt.kind,
        status=attempt.status,
        entry_id=entry.id,
        attempts_used=entry.attempts if not debrief else entry.debrief_attempts,
    )


async def record_started_attempt(
    session: AsyncSession, *, set_entry_id: uuid.UUID, debrief: bool, limit: int, at: datetime
) -> bool:
    """Count one attempt against its entry's limit, now that it has actually started.

    Called from `attempts.service_worker.bootstrap` at the moment a worker first fetches the
    attempt — the earliest point anything tells us the candidate began the consultation rather than
    merely opening the page that created the attempt row (see `start_entry_attempt`). Returns
    whether the count applied; `False` means the limit was already spent, which only happens if a
    race let two attempts against the same entry both reach this point at once — the same guarantee
    `start_entry_attempt` used to keep by incrementing in its own transaction, kept here instead
    because this is now the point that is actually true.
    """
    set_id = await repository.try_record_started_attempt(
        session, set_entry_id, at=at, limit=limit, debrief=debrief
    )
    if set_id is None:
        return False
    if not debrief:
        # A debrief does not move a station from unattempted to attempted, so only a real
        # consultation starting is worth re-checking the whole set's completion for.
        entries = await repository.entries_for(session, set_id)
        if domain.set_complete(
            [
                domain.EntryState(attempts=set_entry.attempts, debrief_attempts=set_entry.debrief_attempts)
                for set_entry in entries
            ]
        ):
            await repository.mark_complete(session, set_id, at=at)
    return True


async def flag_entry(
    session: AsyncSession,
    owner_user_id: uuid.UUID,
    set_id: uuid.UUID,
    entry_id: uuid.UUID,
    *,
    flagged: bool,
    now: datetime,
) -> SetRead:
    """Flag a station in your own set to come back to, or take the flag off.

    Allowed on a locked set: a flag changes nothing about access, and the
    learner may be marking what to revisit once they renew. Flagging twice
    keeps the first time it was flagged.
    """
    station_set = await _require(session, owner_user_id, set_id)
    entry = await repository.entry_by_id(session, set_id, entry_id)
    if entry is None:
        raise errors.EntryNotFound()
    if not flagged:
        await repository.set_entry_flag(session, set_id, entry_id, flagged_at=None)
    elif entry.flagged_at is None:
        await repository.set_entry_flag(session, set_id, entry_id, flagged_at=now)
    return await read_set(session, owner_user_id, station_set.id)


async def list_flagged(
    session: AsyncSession,
    owner_user_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None,
    search: str | None = None,
) -> tuple[list[FlaggedEntryRead], str | None]:
    """One page of the stations this person has flagged across their sets, most recent first.

    `search` matches the set name or the station title, in SQL. Titles come from `stations`
    in one read for the page.
    """
    matching_version_ids = (
        await stations_reads.version_ids_matching_title(session, search) if search else None
    )
    flagged, next_cursor = await repository.flagged_entries_page(
        session,
        owner_user_id,
        limit=limit,
        cursor=cursor,
        search=search,
        matching_version_ids=matching_version_ids,
    )
    summaries = await stations_reads.summaries_by_version_id(
        session, None, [entry.station_version_id for entry, _ in flagged]
    )
    exam_codes = await catalog.exam_codes_by_id(session, [station_set.exam_id for _, station_set in flagged])
    reads = []
    for entry, station_set in flagged:
        if entry.flagged_at is None:  # the query filters these out; this narrows the type
            continue
        summary = summaries.get(entry.station_version_id)
        reads.append(
            FlaggedEntryRead(
                set_id=station_set.id,
                set_name=station_set.name,
                exam_code=exam_codes.get(station_set.exam_id, ""),
                entry_id=entry.id,
                station_version_id=entry.station_version_id,
                station_title=summary.title if summary is not None else None,
                flagged_at=entry.flagged_at,
            )
        )
    return reads, next_cursor


async def _require(session: AsyncSession, owner_user_id: uuid.UUID, set_id: uuid.UUID) -> StationSet:
    """Load a set this owner may act on, or refuse `set_not_found` if it is not theirs."""
    station_set = await repository.set_by_id(session, owner_user_id, set_id)
    if station_set is None:
        raise errors.SetNotFound()
    return station_set


async def _set_read(
    session: AsyncSession, station_set: StationSet, exam_code: str, entries: list[StationSetEntry]
) -> SetRead:
    """Turn a stored set and its entries into the shape a client reads.

    One query answers "what did the newest attempt on each entry reach" for
    every entry in the set at once (`latest_status_by_set_entry`), rather than
    asking `attempts` once per entry — a set can hold a dozen stations, and this
    is read every time the session list loads.
    """
    states = [
        domain.EntryState(attempts=entry.attempts, debrief_attempts=entry.debrief_attempts)
        for entry in entries
    ]
    attempted, total = domain.progress(states)
    latest_status_by_entry = await attempts_reads.latest_status_by_set_entry(
        session, [entry.id for entry in entries]
    )
    # Titles only for stations sat here: a station's name gives its case away before then.
    sat_summaries = await stations_reads.summaries_by_version_id(
        session, None, [entry.station_version_id for entry in entries if entry.attempts > 0]
    )
    entry_reads = []
    any_feedback_ready = False
    for entry in entries:
        last_status = latest_status_by_entry.get(entry.id)
        entry_feedback_ready = last_status == "evaluated"
        summary = sat_summaries.get(entry.station_version_id) if entry.attempts > 0 else None
        any_feedback_ready = any_feedback_ready or entry_feedback_ready
        entry_reads.append(
            EntryRead(
                id=entry.id,
                position=entry.position,
                station_version_id=entry.station_version_id,
                attempts=entry.attempts,
                debrief_attempts=entry.debrief_attempts,
                last_attempt_at=entry.last_attempt_at,
                last_attempt_status=last_status,
                feedback_ready=entry_feedback_ready,
                flagged_at=entry.flagged_at,
                station_title=summary.title if summary is not None else None,
            )
        )
    return SetRead(
        id=station_set.id,
        name=station_set.name,
        exam_code=exam_code,
        locked=station_set.locked,
        completed_at=station_set.completed_at,
        attempted_entries=attempted,
        total_entries=total,
        entries=entry_reads,
        feedback_ready=any_feedback_ready,
    )


async def set_counts_by_station_version(
    session: AsyncSession, station_version_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """How many practice sets include each station version, for an author
    deciding whether a version is safe to throw away."""
    return await repository.set_counts_by_station_version(session, station_version_ids)
