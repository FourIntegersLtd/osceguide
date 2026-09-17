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
from app.features.attempts.service_reads import _attempt_read, _ensure_visible, _require
from app.features.catalog.errors import UnknownExamError as CatalogUnknownExam
from app.features.catalog.service import resolve_exam
from app.features.entitlements import service as entitlements
from app.features.identity import service as identity


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

    The entitlement check happens here rather than in each caller, so every
    route that can start a session goes through the same gate.
    """
    try:
        exam = await resolve_exam(session, exam_code, org_id=org_id)
    except CatalogUnknownExam as exc:
        raise errors.UnknownExamError(str(exc)) from exc

    await entitlements.require(
        session,
        user_id=user_id,
        exam_id=exam.id,
        now=now,
        trial=await _trial_state(session, user_id=user_id, exam_id=exam.id),
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


async def _trial_state(
    session: AsyncSession, *, user_id: uuid.UUID, exam_id: uuid.UUID
) -> entitlements.TrialState | None:
    """What the free-trial rule needs to know about this person.

    Built here rather than in `entitlements`, which sits below this slice and
    so cannot count attempts. That seam is why the rule went unwired: the
    argument defaulted to None, `decide` skips the trial branch entirely when
    it is None, and a brand-new account was refused outright.
    """
    user = await identity.user_ref_by_id(session, user_id)
    if user is None:
        return None
    set_stations, completed = await repository.trial_counts(session, user_id, exam_id)
    return entitlements.TrialState(
        set_station_count=set_stations,
        completed_attempt_count=completed,
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

    Without this an abandoned session stays `running` forever: it holds the
    slot's one live attempt, so a re-dispatch is the only way out, and the
    dashboard counts it as in progress. Recorded as a failure with a reason
    rather than a status of its own, because that is what it is to the marking
    job — there is no transcript to score.
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
    feedback_template_version_id: uuid.UUID | None = None,
) -> Attempt:
    """The attempt a supervisor's dispatch will run (C6).

    Any attempt still live on this slot is failed first, then a new one is
    created. b2b reused the slot's single transcript column, so re-dispatching
    a station silently overwrote the first recording; failing the old attempt
    keeps it, its transcript and its marking, and the partial unique index on
    `(slot_id) where status <> 'failed'` is what makes "at most one live" the
    database's rule rather than this function's.

    No entitlement check: a trainee sitting an exam their institution
    scheduled is not buying anything.
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
        feedback_template_version_id=feedback_template_version_id,
    )


async def _exam_for_station(session: AsyncSession, station_version_id: uuid.UUID | None) -> uuid.UUID:
    """Which exam this slot's station belongs to.

    Read from the station rather than passed in, so a circuit cannot schedule a
    PLAB station under an SCA sitting and have the attempt marked against the
    wrong framework.
    """
    if station_version_id is None:
        raise errors.UnknownExamError("The slot has no station, so there is nothing to run.")
    exam_id = await repository.exam_for_station_version(session, station_version_id)
    if exam_id is None:
        raise errors.UnknownExamError("The slot's station is not bound to an exam.")
    return exam_id


async def latest_attempt_for_set_entry(session: AsyncSession, set_entry_id: uuid.UUID) -> uuid.UUID | None:
    """The attempt a debrief of this set station would be about.

    A debrief has to name the attempt it discusses — the table says so with a
    CHECK — and `station_sets` passed None, so asking for one raised an
    IntegrityError and answered 500.
    """
    attempt = await repository.latest_for_set_entry(session, set_entry_id)
    return None if attempt is None else attempt.id
