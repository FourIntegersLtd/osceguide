"""Attempt use cases, including the worker side of the contract."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import domain, errors, repository
from app.features.attempts.models import Attempt
from app.features.attempts.schemas import (
    AttemptRead,
)
from app.features.attempts.service_debrief import start_debrief_attempt as start_debrief_attempt
from app.features.attempts.service_reads import _attempt_read, _ensure_visible, _require
from app.features.catalog.errors import UnknownExamError as CatalogUnknownExam
from app.features.catalog.service import resolve_exam
from app.features.entitlements import service as entitlements
from app.features.identity import service as identity
from app.features.stations import service as stations
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
) -> AttemptRead:
    """Create an attempt, once access has been established.

    The entitlement check happens here rather than in each caller, so every route that can start
    a session goes through the same gate. `station_version_id` is checked against the same resolver
    the worker bootstrap uses, so a draft station, or one belonging to another organisation, is
    refused when the attempt is created rather than once a candidate is already in the LiveKit room.
    """
    if station_version_id is not None:
        await _ensure_runnable(session, org_id=org_id, station_version_id=station_version_id)
    try:
        exam = await resolve_exam(session, exam_code, org_id=org_id)
    except CatalogUnknownExam as exc:
        raise errors.UnknownExamError(str(exc)) from exc

    # Reopening a station (a reload, a second tab) resumes the attempt it already opened rather
    # than leaving that one orphaned and restarting the reading clock. Checked before the
    # entitlement gate: that attempt was already granted, and the trial counts it.
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

    await entitlements.require(
        session,
        user_id=user_id,
        exam_id=exam.id,
        now=now,
        trial=await trial_state_for(
            session, user_id=user_id, exam_id=exam.id, station_version_id=station_version_id
        ),
    )

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
    return _attempt_read(attempt)


async def _ensure_runnable(
    session: AsyncSession, *, org_id: uuid.UUID | None, station_version_id: uuid.UUID
) -> None:
    """Refuse a station this caller cannot run, before the attempt exists.

    `runnable_station` raises `station_not_published` for a draft itself; a station that does not
    exist and one belonging to another organisation both come back as `None` and both answer
    `station_not_found` — telling them apart would let this route enumerate another tenant's library.
    """
    if await stations.runnable_station(session, org_id, station_version_id) is None:
        raise errors.StationNotFound()


async def require_entitlement(
    session: AsyncSession, *, user_id: uuid.UUID, exam_id: uuid.UUID, now: datetime
) -> None:
    """The same entitlement gate `POST /attempts` applies, for callers that need the trial counts too.

    Peer practice, the marketplace and practice sets all have to ask the same question. One function
    keeps the free trial a single rule: calling `entitlements.require` directly with `trial=None`
    made `decide` skip the trial branch and refuse a brand-new account outright — the bug this closes.
    """
    await entitlements.require(
        session,
        user_id=user_id,
        exam_id=exam_id,
        now=now,
        trial=await trial_state_for(session, user_id=user_id, exam_id=exam_id),
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
        account_created_at=user.created_at,
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

    exam_id = await repository.exam_for_slot_attempt(session, slot_id) if live else None
    return await repository.create_attempt(
        session,
        kind="exam_slot",
        user_id=user_id,
        exam_id=exam_id or await _exam_for_station(session, station_version_id),
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
