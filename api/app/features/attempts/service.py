"""Attempt use cases, including the worker side of the contract."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import savepoint
from app.core.settings import get_settings
from app.features.attempts import domain, errors, repository, service_render
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.models import Attempt
from app.features.attempts.schemas import (
    AttemptRead,
)
from app.features.attempts.service_debrief import start_debrief_attempt as start_debrief_attempt
from app.features.attempts.service_reads import _attempt_read, _ensure_visible, _require
from app.features.catalog.errors import UnknownExamError as CatalogUnknownExam
from app.features.catalog.service import exam_for_attempt, resolve_exam
from app.features.entitlements import service as entitlements
from app.features.entitlements.errors import NotEntitled
from app.features.identity import service as identity
from app.features.identity import service_platform as identity_accounts
from app.features.stations import service as stations
from app.features.stations import service_plan_window
from app.features.stations import service_reads as stations_reads

# The consumer kinds a reload reopens: one person, one station, nothing scheduled around them.
_RESUMABLE_KINDS = frozenset({"practice", "set_station", "self_practice"})


async def start_attempt(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    kind: str,
    exam_code: str,
    now: datetime,
    org_id: uuid.UUID | None = None,
    station_version_id: uuid.UUID | None = None,
    slot_id: uuid.UUID | None = None,
    set_entry_id: uuid.UUID | None = None,
    peer_session_id: uuid.UUID | None = None,
    source_attempt_id: uuid.UUID | None = None,
    room_name: str | None = None,
    entitled_at: datetime | None = None,
) -> AttemptRead:
    """Create an attempt, once access has been established.

    `entitled_at` is the instant access is judged at, `now` when omitted. Marking a peer session that
    already happened passes when it started, so a transcript that lands after the trial closed is
    still scored.

    The entitlement check happens here rather than in each caller, so every route that can start
    a session goes through the same gate. `station_version_id` is checked against the same resolver
    the worker bootstrap uses, so a draft station, or one belonging to another organisation, is
    refused when the attempt is created rather than once a candidate is already in the LiveKit room.
    """
    runnable = None
    if station_version_id is not None:
        runnable = await _ensure_runnable(session, org_id=org_id, station_version_id=station_version_id)
    try:
        exam = await resolve_exam(session, exam_code, org_id=org_id)
    except CatalogUnknownExam as exc:
        raise errors.UnknownExamError(str(exc)) from exc
    # Against the exam resolved above, not the raw code: an org may resolve its own exam of that code.
    # Before entitlement, so the refusal never depends on what the caller holds.
    if runnable is not None and runnable.exam_id != exam.id:
        raise errors.StationExamMismatch()

    # A peer session is time-limited, not counted: marking one asks only whether the trial's days remain.
    await require_entitlement(
        session,
        user_id=user_id,
        exam_id=exam.id,
        now=entitled_at or now,
        station_version_id=station_version_id,
        window_only=kind == domain.Kind.PEER,
    )
    if runnable is not None:
        await service_plan_window.ensure_station_in_plan(
            session,
            user_id=user_id,
            station_id=runnable.station_id,
            owner_kind=runnable.owner_kind,
            exam_id=runnable.exam_id,
            now=now,
        )

    # Reopening a station (a reload, a second tab) resumes the attempt it already opened rather
    # than leaving that one orphaned and restarting the reading clock. Checked after the
    # entitlement gate (S-11): access that has lapsed or been refunded since must not reopen it.
    if kind in _RESUMABLE_KINDS and station_version_id is not None and room_name is None:
        unstarted = await repository.unstarted_attempt(
            session,
            kind=kind,
            user_id=user_id,
            exam_id=exam.id,
            org_id=org_id,
            station_version_id=station_version_id,
            set_entry_id=set_entry_id,
        )
        if unstarted is not None:
            return _attempt_read(unstarted)

    try:
        # A savepoint, so losing the race below rolls back only this insert, not the caller's work.
        async with savepoint(session):
            attempt = await repository.create_attempt(
                session,
                kind=kind,
                user_id=user_id,
                exam_id=exam.id,
                org_id=org_id,
                station_version_id=station_version_id,
                slot_id=slot_id,
                set_entry_id=set_entry_id,
                peer_session_id=peer_session_id,
                source_attempt_id=source_attempt_id,
                room_name=room_name,
            )
    except IntegrityError as exc:
        # A double click or retry started the same station a moment ago: hand back that attempt.
        if getattr(getattr(exc.orig, "diag", None), "constraint_name", None) != "uq_attempts_one_unstarted":
            raise
        winner = await repository.unstarted_attempt(
            session,
            kind=kind,
            user_id=user_id,
            exam_id=exam.id,
            org_id=org_id,
            station_version_id=station_version_id,
            set_entry_id=set_entry_id,
        )
        if winner is None:
            raise
        return _attempt_read(winner)
    return _attempt_read(attempt)


async def _ensure_runnable(
    session: AsyncSession, *, org_id: uuid.UUID | None, station_version_id: uuid.UUID
) -> stations.RunnableStation:
    """Refuse a station this caller cannot run, before the attempt exists.

    `runnable_station` raises `station_not_published` for a draft itself; a station that does not
    exist and one belonging to another organisation both come back as `None` and both answer
    `station_not_found` — telling them apart would let this route enumerate another tenant's library.
    """
    runnable = await stations.runnable_station(session, org_id, station_version_id)
    if runnable is None:
        raise errors.StationNotFound()
    return runnable


async def require_entitlement(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    exam_id: uuid.UUID,
    now: datetime,
    station_version_id: uuid.UUID | None = None,
    window_only: bool = False,
) -> None:
    """The same entitlement gate `POST /attempts` applies, for callers that need the trial counts too.

    Peer practice, the marketplace and practice sets all have to ask the same question. One function
    keeps the free trial a single rule: calling `entitlements.require` directly with `trial=None`
    made `decide` skip the trial branch and refuse a brand-new account outright — the bug this closes.
    With `station_version_id`, a trial station already counted is not counted again against itself.
    With `window_only`, the trial's fourteen days are the whole limit: its station and attempt counts
    are ignored. That is peer practice, which is time-limited rather than counted.
    """
    trial = await trial_state_for(
        session, user_id=user_id, exam_id=exam_id, station_version_id=station_version_id
    )
    if window_only and trial is not None:
        trial = replace(trial, set_station_count=0, completed_station_count=0, completed_on_this_station=None)
    await entitlements.require(session, user_id=user_id, exam_id=exam_id, now=now, trial=trial)


async def window_is_open(
    session: AsyncSession, *, user_id: uuid.UUID, exam_id: uuid.UUID, now: datetime
) -> bool:
    """Whether `require_entitlement(window_only=True)` would let this person in, without raising.

    For a caller that must act on the answer for someone else (end a pairing, cancel a booking) and
    so cannot let a refusal abort its own transaction.
    """
    try:
        await require_entitlement(session, user_id=user_id, exam_id=exam_id, now=now, window_only=True)
    except NotEntitled:
        return False
    return True


async def ensure_entitled_to_begin(session: AsyncSession, attempt: Attempt, *, now: datetime) -> None:
    """The start boundary (S-11): an attempt created while entitled is checked again as it begins.

    Only a consumer attempt that has not begun is held to it. Once running it is never cut off:
    access that ends mid-attempt lets that attempt finish (its turns and its submission are not
    re-checked) and only a new attempt is refused, at `start_attempt`.
    """
    if attempt.kind not in _RESUMABLE_KINDS or attempt.status != "created":
        return
    await require_entitlement(
        session,
        user_id=attempt.user_id,
        exam_id=attempt.exam_id,
        now=now,
        station_version_id=attempt.station_version_id,
    )


async def trial_state_for(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    exam_id: uuid.UUID,
    station_version_id: uuid.UUID | None = None,
) -> entitlements.TrialState | None:
    """What the free-trial rule needs to know about this person.

    Built here, not in `entitlements`, which cannot count attempts itself. Public because the other
    things somebody may do on their free trial — queueing for a peer session, offering a slot,
    building a practice set — must apply the same rule rather than a second definition of it.
    """
    user = await identity.user_ref_by_id(session, user_id)
    if user is None:
        return None
    trial_attempts = await repository.attempts_counted_by_trial(session, user_id, exam_id)
    version_ids = {
        trial_attempt.station_version_id
        for trial_attempt in trial_attempts
        if trial_attempt.station_version_id is not None
    }
    if station_version_id is not None:
        version_ids.add(station_version_id)
    version_stations = await stations_reads.stations_by_version_id(session, list(version_ids))
    station_by_version = {
        version_id: version_station.station_id for version_id, version_station in version_stations.items()
    }
    counts = domain.count_trial_use(
        trial_attempts,
        station_by_version=station_by_version,
        starting_station_id=station_by_version.get(station_version_id) if station_version_id else None,
    )
    return entitlements.TrialState(
        set_station_count=counts.set_stations,
        completed_station_count=counts.completed_stations,
        completed_on_this_station=counts.completed_on_this_station if counts.started_this_station else None,
        trial_started_at=user.trial_started_at,
    )


async def abandon_attempt(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    requester_id: uuid.UUID,
    is_admin: bool,
    now: datetime,
) -> AttemptRead:
    """The candidate walks away.

    Without this an abandoned session stays `running` forever, holding the slot's one live attempt.
    Recorded as a failure with a reason rather than a status of its own — to the marking job that is
    what it is, since there is no transcript to score.
    """
    attempt = await _require(session, attempt_id)
    _ensure_visible(attempt, requester_id=requester_id, is_admin=is_admin)
    try:
        domain.ensure_abandonable(domain.Status(attempt.status))
    except domain.InvalidTransition as exc:
        raise errors.InvalidAttemptState(str(exc)) from exc

    await repository.set_status(session, attempt_id, status=domain.Status.FAILED, at=now, reason="abandoned")
    return _attempt_read(await _require(session, attempt_id))


ABANDONED_AFTER = timedelta(hours=3)


async def attempt_deadline(session: AsyncSession, attempt: Attempt) -> datetime | None:
    """When the server stops taking turns for this attempt, or None while it has no clock.

    Only a started consumer station is timed here; an exam slot's circuit owns its own clock.
    The person's own timers win over the exam's defaults, as on the station runner.
    """
    if attempt.started_at is None or attempt.kind not in _RESUMABLE_KINDS:
        return None
    exam = await exam_for_attempt(session, attempt.exam_id)
    person = await identity_accounts.user_by_id(session, attempt.user_id)
    reading = exam.default_reading_seconds
    simulation = exam.default_simulation_seconds
    if person is not None and person.needs_extra_time:  # custom timers count only with extra time on
        reading = person.custom_reading_seconds or reading
        simulation = person.custom_simulation_seconds or simulation
    return domain.attempt_deadline(
        attempt.started_at, reading, simulation, get_settings().attempt_deadline_grace_seconds
    )


async def _close_overdue(session: AsyncSession, attempt_id: uuid.UUID, turns: int, *, now: datetime) -> bool:
    """Close one overdue attempt under the transcript lock, unless the worker finished it meanwhile."""
    from app.features.attempts import service_worker  # deferred: service_worker imports this module

    await transcripts.lock_transcript(session, attempt_id)
    attempt = await repository.attempt_by_id(session, attempt_id)
    if attempt is None or domain.Status(attempt.status) is not domain.Status.RUNNING:
        return False
    if turns:
        await transcripts.mark_transcript_complete(session, attempt_id, runtime_label="deadline", at=now)
        await service_worker.complete_interaction(session, attempt, now=now)
    else:
        await repository.set_status(
            session, attempt_id, status=domain.Status.FAILED, at=now, reason="abandoned"
        )
    return True


async def abandon_stale_attempts(session: AsyncSession, *, now: datetime) -> list[uuid.UUID]:
    """Close the consumer attempts nobody finished (S-25); returns the ids closed.

    Over three hours created or running: failed `abandoned`, the tab was closed. A running station
    past its own deadline (duration plus grace): its turns are marked as if the worker had delivered
    them, or `abandoned` when there are none, so a dropped worker never strands a mark.
    """
    closed = await repository.fail_stale_consumer_attempts(
        session, started_before=now - ABANDONED_AFTER, at=now, reason="abandoned"
    )
    grace = timedelta(seconds=get_settings().attempt_deadline_grace_seconds)
    candidates = await repository.running_attempts_started_before(
        session, started_before=now - grace, kinds=sorted(_RESUMABLE_KINDS)
    )
    overdue: list[Attempt] = []
    for candidate in candidates:
        deadline = await attempt_deadline(session, candidate)
        if deadline is not None and deadline < now:
            overdue.append(candidate)
    turn_counts = await transcripts.chunk_counts_for(
        session, [overdue_attempt.id for overdue_attempt in overdue]
    )
    for overdue_attempt in overdue:
        if await _close_overdue(session, overdue_attempt.id, turn_counts.get(overdue_attempt.id, 0), now=now):
            closed.append(overdue_attempt.id)
    return closed


async def restart_for_slot(
    session: AsyncSession,
    *,
    slot_id: uuid.UUID,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    station_version_id: uuid.UUID | None,
    room_name: str,
    now: datetime,
) -> Attempt:
    """The attempt a supervisor's dispatch will run.

    Any attempt still live on this slot is failed first, then a new one is created. b2b once reused
    the slot's single transcript column, so re-dispatching silently overwrote the first recording;
    failing the old attempt keeps it, its transcript and its marking, and the partial unique index
    on `(slot_id) where status <> 'failed'` is what enforces "at most one live" in the database.

    No entitlement check: a trainee sitting an exam their institution scheduled is not buying anything.
    """
    live = await repository.live_attempt_for_slot(session, slot_id)
    await repository.fail_live_attempt_for_slot(session, slot_id, at=now, reason="redispatched")

    exam_id = (await repository.exam_for_slot_attempt(session, slot_id) if live else None) or (
        await _exam_for_station(session, station_version_id)
    )
    await service_render.ensure_slot_markable(session, org_id=org_id, slot_id=slot_id, exam_id=exam_id)
    return await repository.create_attempt(
        session,
        kind="exam_slot",
        user_id=user_id,
        exam_id=exam_id,
        org_id=org_id,
        station_version_id=station_version_id,
        slot_id=slot_id,
        room_name=room_name,
    )


async def fail_live_for_slot(
    session: AsyncSession, *, slot_id: uuid.UUID, now: datetime, reason: str
) -> None:
    """End whatever recording this slot has, without starting another.

    Failed rather than deleted, so what happened the first time survives beside the retry, and the
    partial unique index will accept the new one.
    """
    await repository.fail_live_attempt_for_slot(session, slot_id, at=now, reason=reason)


async def fail_unfinished_for_user(
    session: AsyncSession, *, user_id: uuid.UUID, now: datetime, reason: str
) -> int:
    """End every consultation this person has open, for an account that has just been closed.

    Failed with a reason rather than deleted, like an abandon, so what was recorded survives.
    """
    return await repository.fail_unfinished_for_user(session, user_id, at=now, reason=reason)


async def _exam_for_station(session: AsyncSession, station_version_id: uuid.UUID | None) -> uuid.UUID:
    """Which exam this slot's station belongs to.

    Read from the station rather than passed in, so a circuit cannot schedule a PLAB station under an
    SCA sitting and have the attempt marked against the wrong framework.
    """
    if station_version_id is None:
        raise errors.UnknownExamError("The slot has no station, so there is nothing to run.")
    version_station = (await stations_reads.stations_by_version_id(session, [station_version_id])).get(
        station_version_id
    )
    if version_station is None:
        raise errors.UnknownExamError("The slot's station is not bound to an exam.")
    return version_station.exam_id


async def latest_attempt_for_set_entry(session: AsyncSession, set_entry_id: uuid.UUID) -> uuid.UUID | None:
    """The attempt a debrief of this set station would be about.

    A debrief has to name the attempt it discusses (a CHECK on the table); `station_sets` once passed
    None here, so asking for one raised an IntegrityError and answered 500.
    """
    attempt = await repository.latest_for_set_entry(session, set_entry_id)
    return None if attempt is None else attempt.id


async def attempt_counts_by_station_version(
    session: AsyncSession, station_version_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """How many attempts were made against each station version, for an
    author deciding whether a version is safe to throw away."""
    return await repository.attempt_counts_by_station_version(session, station_version_ids)
