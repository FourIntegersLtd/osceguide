"""Scheduling a sitting: creating one, and building the circuits inside it.

Running a circuit is `service_run.py`: this one moves when an examination is
*composed* differently, that one when it is *run* differently.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, raise_mapped
from app.features.catalog import service as catalog
from app.features.identity import service as identity
from app.features.roster import service as roster
from app.features.roster import service_groups as roster_groups
from app.features.rubrics import service_marking
from app.features.sittings import (
    announcements,
    domain,
    domain_edit,
    domain_run,
    errors,
    repository,
    repository_reads,
    repository_run,
    service_notify,
)
from app.features.sittings.models import Circuit, Sitting, Slot
from app.features.sittings.reads import circuit_read, sitting_read, timing_input, timing_json
from app.features.sittings.schemas import CircuitRead, CreateExamCircuits, SittingRead, TimingIn
from app.features.tenancy import service as tenancy

# One place mapping a domain refusal to its API code — the running rules
# included, so an override and a structural edit cannot answer differently for
# the same reason.
_REFUSALS: dict[type[Exception], type[AppError]] = {
    domain.InvalidCircuit: errors.InvalidCircuitError,
    domain.CircuitLocked: errors.CircuitLockedError,
    domain.CircuitAlreadyEnded: errors.CircuitAlreadyEndedError,
    domain.NotPermittedInMode: errors.NotPermittedInModeError,
    domain_run.CircuitPaused: errors.CircuitPausedError,
    domain_run.CircuitNotPaused: errors.CircuitNotPausedError,
    domain_edit.SittingLocked: errors.SittingLockedError,
    domain_edit.TraineeAlreadyOnCircuit: errors.TraineeAlreadyOnCircuitError,
    domain_edit.StationNotOnCircuit: errors.StationNotOnCircuitError,
}


async def open_sittings_using_rubric_version(session: AsyncSession, rubric_version_id: uuid.UUID) -> int:
    """How many sittings marked against this rubric version still have a circuit to run."""
    return await repository.count_open_sittings_for_rubric_version(session, rubric_version_id)


async def create_sitting(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    name: str,
    mode: str,
    sitting_type: str,
    scheduled_for: datetime | None,
    programme_id: uuid.UUID,
    cohort_id: uuid.UUID | None = None,
) -> SittingRead:
    """Schedule a new sitting, marked against its programme's published rubric."""
    rubric_version_id = await rubric_version_for_programme(session, org_id, programme_id)
    if cohort_id is not None:
        await roster_groups.require_cohort(session, org_id, cohort_id)

    sitting = await repository.create_sitting(
        session,
        org_id,
        name=name,
        rubric_version_id=rubric_version_id,
        mode=mode,
        sitting_type=sitting_type,
        scheduled_for=scheduled_for,
        programme_id=programme_id,
        cohort_id=cohort_id,
    )
    return (await _with_totals(session, org_id, [sitting_read(sitting, [])]))[0]


async def read_sitting(session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID) -> SittingRead:
    """A sitting with every circuit and slot it has, for a console screen."""
    sitting = await _require_sitting(session, org_id, sitting_id)
    reads: list[CircuitRead] = []
    for circuit in await repository.circuits_for_sitting(session, org_id, sitting_id):
        slots = await repository.slots_for_circuit(session, org_id, circuit.id)
        reads.append(circuit_read(circuit, slots))
    supervisors = await identity.user_refs_by_ids(
        session, [read.supervisor_user_id for read in reads if read.supervisor_user_id]
    )
    for read in reads:
        person = supervisors.get(read.supervisor_user_id) if read.supervisor_user_id else None
        read.supervisor_name = (person.name or person.email) if person else None
    return (await _with_totals(session, org_id, [sitting_read(sitting, reads)]))[0]


async def list_sittings(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None,
    status: str | None = None,
    mode: str | None = None,
    search: str | None = None,
    programme_id: uuid.UUID | None = None,
    scheduled_from: date | None = None,
    scheduled_to: date | None = None,
) -> tuple[list[SittingRead], str | None]:
    """A page of this organisation's sittings, newest first; the dates are inclusive days (R-31)."""
    sittings, next_cursor = await repository.list_sittings(
        session,
        org_id,
        limit=limit,
        cursor=cursor,
        status=status,
        mode=mode,
        search=search,
        programme_id=programme_id,
        scheduled_from=_start_of(scheduled_from),
        scheduled_to=_start_of(scheduled_to + timedelta(days=1)) if scheduled_to else None,
    )
    return await _with_totals(
        session, org_id, [sitting_read(sitting, []) for sitting in sittings]
    ), next_cursor


def _start_of(day: date | None) -> datetime | None:
    return datetime(day.year, day.month, day.day, tzinfo=UTC) if day else None


async def _with_totals(
    session: AsyncSession, org_id: uuid.UUID, reads: list[SittingRead]
) -> list[SittingRead]:
    """Fill each sitting's programme name, exam code and candidate count, a few queries for the lot."""
    programme_ids = [read.programme_id for read in reads if read.programme_id]
    exams = await catalog.programme_exams(session, org_id, programme_ids)
    counts = await repository_reads.candidate_counts_for_sittings(
        session, org_id, [read.id for read in reads]
    )
    for sitting in reads:
        if sitting.programme_id in exams:
            sitting.programme_name, sitting.exam_code = exams[sitting.programme_id]
        sitting.candidate_count = counts.get(sitting.id, 0)
    return reads


async def ensure_lead_may_run(session: AsyncSession, org_id: uuid.UUID, lead: uuid.UUID | None) -> None:
    """R-38: a circuit's lead runs it, so a trainee or a stranger cannot be named."""
    if lead is not None and not await tenancy.may_run_circuits(session, org_id, lead):
        raise errors.LeadCannotRun()


async def add_circuit(
    session: AsyncSession,
    org_id: uuid.UUID,
    sitting_id: uuid.UUID,
    *,
    name: str,
    trainee_ids: list[uuid.UUID],
    station_version_ids: list[uuid.UUID],
    supervisor_user_id: uuid.UUID | None,
    timing: TimingIn,
) -> CircuitRead:
    """Build a new circuit inside a sitting: check the sitting, then build and write the circuit."""
    sitting = await _open_sitting(session, org_id, sitting_id)
    return await _create_circuit(
        session,
        org_id,
        sitting,
        name=name,
        trainee_ids=trainee_ids,
        station_version_ids=station_version_ids,
        supervisor_user_id=supervisor_user_id,
        timing=timing,
    )


async def add_exam_circuits(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID, body: CreateExamCircuits
) -> list[CircuitRead]:
    """One exam circuit per candidate, same stations, lead and timing; the request's transaction
    makes it all or none."""
    sitting = await _open_sitting(session, org_id, sitting_id)
    if domain.Mode(sitting.mode) is not domain.Mode.EXAM:
        raise errors.NotPermittedInModeError("Separate circuits per candidate are for exam sittings.")
    await roster.ensure_rosterable(session, org_id, body.candidate_user_ids)
    names = await roster.names_for_users(session, org_id, body.candidate_user_ids)
    return [
        await _create_circuit(
            session,
            org_id,
            sitting,
            # The column holds 200 characters; a long prefix plus name is cut to fit.
            name=f"{body.name_prefix} – {names[candidate]}"[:200],
            trainee_ids=[candidate],
            station_version_ids=body.station_version_ids,
            supervisor_user_id=body.supervisor_user_id,
            timing=body.timing or TimingIn(),
        )
        for candidate in body.candidate_user_ids
    ]


async def _open_sitting(session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID) -> Sitting:
    """The sitting, if it exists here, is not locked and its programme is active."""
    sitting = await _require_sitting(session, org_id, sitting_id)
    await ensure_sitting_open(session, org_id, sitting)
    await ensure_sitting_programme_active(session, org_id, sitting)
    return sitting


async def _create_circuit(
    session: AsyncSession,
    org_id: uuid.UUID,
    sitting: Sitting,
    *,
    name: str,
    trainee_ids: list[uuid.UUID],
    station_version_ids: list[uuid.UUID],
    supervisor_user_id: uuid.UUID | None,
    timing: TimingIn,
) -> CircuitRead:
    """Check the roster, build the slots, write the circuit and tell the people on it."""
    mode = domain.Mode(sitting.mode)
    # R3: a revoked trainee is not scheduled into an examination.
    await roster.ensure_rosterable(session, org_id, trainee_ids)
    await ensure_lead_may_run(session, org_id, supervisor_user_id)

    try:
        planned = domain.build_slots(
            mode,
            trainee_user_ids=[str(trainee_id) for trainee_id in trainee_ids],
            station_version_ids=[str(station_version_id) for station_version_id in station_version_ids],
        )
    except domain.InvalidCircuit as exc:
        raise_mapped(exc, _REFUSALS)

    resolved_timing = domain.normalise_timing(
        timing_input(timing),
        mode=mode,
        station_count=len(station_version_ids),
    )

    circuit = await repository.create_circuit(
        session,
        org_id,
        sitting_id=sitting.id,
        name=name,
        supervisor_user_id=supervisor_user_id,
        timing=timing_json(resolved_timing),
    )
    await repository.add_circuit_members(
        session, circuit.id, trainee_ids=trainee_ids, station_version_ids=station_version_ids
    )
    slots = await repository.create_slots(
        session,
        org_id,
        circuit.id,
        planned=[
            (slot.index, uuid.UUID(slot.trainee_user_id), uuid.UUID(slot.station_version_id))
            for slot in planned
        ],
    )
    await service_notify.trainees_scheduled(session, org_id, sitting, trainee_ids)
    await service_notify.reviewer_assigned(session, org_id, sitting, circuit)
    return circuit_read(circuit, slots)


async def read_circuit(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> CircuitRead:
    """A circuit and its slots as the API shape a console screen reads."""
    circuit = await _require_circuit(session, org_id, circuit_id)
    slots = await repository.slots_for_circuit(session, org_id, circuit_id)
    return circuit_read(circuit, slots)


async def _require_sitting(session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID) -> Sitting:
    """The sitting, or raise `SittingNotFound` if it does not belong to this organisation."""
    sitting = await repository.sitting_by_id(session, org_id, sitting_id)
    if sitting is None:
        raise errors.SittingNotFound()
    return sitting


def ensure_sitting_not_cancelled(sitting: Sitting) -> None:
    """Refuse a cancelled sitting (R-7): what editing or starting one needs.

    A circuit built before sign-off may still run, so these do not ask about results.
    """
    try:
        domain_edit.ensure_sitting_open(cancelled=sitting.status == domain_edit.CANCELLED, settled=False)
    except domain_edit.SittingLocked as exc:
        raise_mapped(exc, _REFUSALS)


async def ensure_sitting_open(session: AsyncSession, org_id: uuid.UUID, sitting: Sitting) -> None:
    """Refuse a cancelled sitting, or one with a signed-off or released result (R-7).

    Adding a circuit or trainees needs both.
    """
    # `results` imports this slice, so its import has to wait until call time
    # (the same as `reviews`); a router may not import another slice to pass it in.
    from app.features.results import service as results

    settled = await results.sitting_has_settled_decision(session, org_id, sitting.id)
    try:
        domain_edit.ensure_sitting_open(cancelled=sitting.status == domain_edit.CANCELLED, settled=settled)
    except domain_edit.SittingLocked as exc:
        raise_mapped(exc, _REFUSALS)


async def _require_circuit(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, *, lock: bool = False
) -> Circuit:
    """Load a circuit, optionally holding it for the rest of the transaction.

    `lock=True` for anything that reads the circuit's state and then writes it
    (C4): start, switch, end. Reads leave it unlocked, so a supervisor console
    polling the state does not queue behind a write.
    """
    fetch = repository.circuit_for_update if lock else repository.circuit_by_id
    circuit = await fetch(session, org_id, circuit_id)
    if circuit is None:
        raise errors.CircuitNotFound()
    return circuit


async def slot_is_in_org(session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID) -> bool:
    """Whether this slot belongs to this organisation.

    Exposed for `reviews`, whose routes are addressed by slot id. A slot id in
    a URL says nothing about who owns it, and taking the org from the path
    while trusting the id is how a review came to be storable against another
    tenant's slot (P4).
    """
    return await repository.slot_by_id(session, org_id, slot_id) is not None


async def slot_and_circuit_for_owner(
    session: AsyncSession, slot_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[Slot, Circuit] | None:
    """The slot and its circuit, if the slot is this signed-in person's own.

    Exposed for `reviews`, whose own read of a slot's review needs the slot's
    org and the circuit's sitting to check the result is released, without
    reaching into this slice's repository directly.
    """
    slot = await repository.slot_by_id_for_user(session, slot_id, user_id)
    if slot is None:
        return None
    circuit = await repository.circuit_by_id(session, slot.org_id, slot.circuit_id)
    if circuit is None:
        return None
    return slot, circuit


async def rubric_version_for_slot(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID
) -> uuid.UUID | None:
    """Which rubric version a slot is marked against (R-1), for `reviews`."""
    return await repository.rubric_version_for_slot(session, org_id, slot_id)


async def rubric_versions_for_slots(
    session: AsyncSession, org_id: uuid.UUID, slot_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, uuid.UUID]:
    """Which rubric version each slot is marked against, for `reviews` scoring many slots at once."""
    return await repository.rubric_versions_for_slots(session, org_id, slot_ids)


# --- Which rubric version a sitting is marked against.


async def ensure_sitting_programme_active(session: AsyncSession, org_id: uuid.UUID, sitting: Sitting) -> None:
    """S-28: a retired or paused programme keeps its sittings but starts nothing new under them."""
    if sitting.programme_id is not None:
        await catalog.ensure_programme_active(session, org_id, sitting.programme_id)


async def rubric_version_for_programme(
    session: AsyncSession, org_id: uuid.UUID, programme_id: uuid.UUID
) -> uuid.UUID:
    """The published rubric version this programme's exam is marked with."""
    exam = await catalog.ensure_programme_active(session, org_id, programme_id)
    if exam.rubric_version_id is None:
        raise errors.ExamRubricNotReady("That programme's exam has no published rubric to mark against yet.")
    await service_marking.published_version(session, org_id, exam.rubric_version_id)
    return exam.rubric_version_id


async def skip_unstarted_stations(
    session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, *, now: datetime
) -> int:
    """For the roster: a person leaving the directory has their unstarted stations ended (S-18)."""
    circuit_ids = await repository.open_circuit_ids_with_unstarted_slots(session, org_id, user_id)
    skipped = await repository_run.skip_unstarted_slots_for_user(session, org_id, user_id, now=now)
    for circuit_id in circuit_ids:
        await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.ABSENT)
    return skipped


async def circuit_counts_by_station_version(
    session: AsyncSession, station_version_ids: list[uuid.UUID], *, open_only: bool = False
) -> dict[uuid.UUID, int]:
    """How many circuits name each station version, for an author deciding
    whether a version is safe to throw away (`open_only`: or to withdraw)."""
    return await repository.circuit_counts_by_station_version(
        session, station_version_ids, open_only=open_only
    )
