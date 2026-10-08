"""Changing who is on a circuit and what they sit.

Appending is allowed *because* a circuit is live (C8); rebuilding is refused
for the same reason (C3) — the two are refused for opposite reasons.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_mapped
from app.core.revision import ensure_current
from app.features.attempts import service_reads as attempts
from app.features.roster import service as roster
from app.features.sittings import (
    announcements,
    domain,
    domain_edit,
    errors,
    repository,
    repository_reads,
    service,
    service_notify,
)
from app.features.sittings.models import Circuit, Slot
from app.features.sittings.reads import state as _state
from app.features.sittings.reads import timing_json
from app.features.sittings.schemas import CircuitRead, TimingIn
from app.features.sittings.service import (
    _REFUSALS,
    _require_circuit,
    _require_sitting,
    ensure_lead_may_run,
    ensure_sitting_open,
)
from app.features.sittings.service_circuit import _any_slot_reviewed


async def append_trainees(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    trainee_ids: list[uuid.UUID],
    station_version_ids: list[uuid.UUID] | None = None,
) -> CircuitRead:
    """Add people to a training circuit that may already be running (C8).

    Training only: an exam circuit is one candidate by construction (C1), and a
    second would make its slots mean something different.

    New slots inherit the circuit's live room — without it a latecomer's slot
    has no room, and the trainee portal has nothing to offer them while a
    session they are in runs without them.
    """
    circuit = await _require_circuit(session, org_id, circuit_id, lock=True)
    sitting = await _require_sitting(session, org_id, circuit.sitting_id)
    try:
        domain.ensure_live(_state(circuit, has_feedback=False))
        domain.ensure_can_append_trainees(domain.Mode(sitting.mode))
    except (domain.CircuitAlreadyEnded, domain.NotPermittedInMode) as exc:
        raise_mapped(exc, _REFUSALS)
    await ensure_sitting_open(session, org_id, sitting)

    await roster.ensure_rosterable(session, org_id, trainee_ids)

    named = station_version_ids or []
    existing = await repository.slots_for_circuit(session, org_id, circuit_id)
    stations = await repository_reads.circuit_station_ids(session, org_id, circuit_id)
    targets = _station_targets(named, _standing_station(circuit, existing, stations), len(trainee_ids))
    if not targets:
        # Nothing to place anybody at — neither a slot nor a station. Refused
        # rather than guessed at, as this route always did; the pairing check
        # below cannot catch it, because an empty target list is otherwise
        # indistinguishable from "no station named".
        raise errors.InvalidCircuitError("This circuit has no station to place anybody at.")
    try:
        domain_edit.ensure_not_already_rostered(
            await repository_reads.circuit_trainee_ids(session, org_id, circuit_id), trainee_ids
        )
        domain_edit.ensure_appended_pairing(len(trainee_ids), len(named))
        domain_edit.ensure_stations_are_on_circuit(targets, stations)
    except (
        domain_edit.TraineeAlreadyOnCircuit,
        domain_edit.StationNotOnCircuit,
        domain.InvalidCircuit,
    ) as exc:
        raise_mapped(exc, _REFUSALS)

    next_index = max((slot.slot_index for slot in existing), default=-1) + 1
    await repository.add_circuit_members(session, circuit_id, trainee_ids=trainee_ids, station_version_ids=[])
    await repository.create_slots(
        session,
        org_id,
        circuit_id,
        planned=[
            (next_index + offset, trainee_id, station_id)
            for offset, (trainee_id, station_id) in enumerate(zip(trainee_ids, targets, strict=True))
        ],
        room_name=circuit.room_name,
    )
    await service_notify.trainees_scheduled(session, org_id, sitting, trainee_ids)
    await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.TRAINEES_APPENDED)
    return await service.read_circuit(session, org_id, circuit_id)


async def delete_circuit(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> None:
    """Remove a circuit nobody has run (R-7): built by mistake, or for a day that was called off.

    A started circuit is kept, whatever happened in it: its run is the record
    of the examination. End it instead.
    """
    circuit = await _require_circuit(session, org_id, circuit_id, lock=True)
    if circuit.started_at is not None:
        raise errors.CircuitLockedError("This circuit has been started, so it is kept. End it instead.")
    await repository_reads.delete_circuit_structure(session, org_id, circuit_id)
    await repository.delete_circuit(session, org_id, circuit_id)


def _standing_station(circuit: Circuit, slots: list[Slot], stations: list[uuid.UUID]) -> uuid.UUID | None:
    """The station an arrival lands on when nobody says otherwise.

    The one the circuit is on, if it is on one — that is what "catch up with us"
    means mid-session. Then the first of its slots, then the first station it was
    given, because a circuit whose rotation has not begun has a station list
    even when nothing has been seated yet. None only when there is neither, which
    is the case the route refuses rather than invents a station for.
    """
    active = next((slot for slot in slots if slot.id == circuit.active_slot_id), None)
    if active is not None:
        return active.station_version_id
    if slots:
        return slots[0].station_version_id
    return stations[0] if stations else None


def _station_targets(
    named: list[uuid.UUID], standing: uuid.UUID | None, trainee_count: int
) -> list[uuid.UUID]:
    """Where each arrival sits.

    Named stations pair with the arrivals positionally, as a circuit's stations
    pair with its trainees when it is built. Nothing named is the one case this
    route has always served: everyone goes to the station the circuit is at.
    """
    if named:
        return list(named)
    return [standing] * trainee_count if standing is not None else []


async def rebuild_circuit(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    trainee_ids: list[uuid.UUID],
    station_version_ids: list[uuid.UUID],
    name: str | None = None,
    supervisor_user_id: uuid.UUID | None = None,
    timing: TimingIn | None = None,
    revision: int | None = None,
) -> CircuitRead:
    """Change who is on a circuit and which stations they sit (C3).

    A structural edit rebuilds the slots, so it is refused once any of them
    means something: a consultation in progress would be deleted mid-sentence,
    and recorded feedback would point at a slot that no longer exists.
    """
    circuit = await _require_circuit(session, org_id, circuit_id, lock=True)
    ensure_current(revision, circuit.revision)
    sitting = await _require_sitting(session, org_id, circuit.sitting_id)
    if circuit.ended_at is not None:
        raise errors.CircuitAlreadyEndedError("That circuit has already finished.")

    slots = await repository.slots_for_circuit(session, org_id, circuit_id)
    has_feedback = await _any_slot_reviewed(session, [slot.id for slot in slots])
    try:
        domain.ensure_editable(_state(circuit, has_feedback=has_feedback))
    except domain.CircuitLocked as exc:
        raise_mapped(exc, _REFUSALS)

    # Feedback is not the only thing worth keeping: an attempt is a recording
    # and a marking, and the slot it hangs off cannot be deleted under it.
    attempted = await attempts.slots_with_attempts(session, [slot.id for slot in slots])
    if attempted:
        raise errors.CircuitLockedError("A station on this circuit has already been run.")

    await roster.ensure_rosterable(session, org_id, trainee_ids)
    await ensure_lead_may_run(session, org_id, supervisor_user_id)
    mode = domain.Mode(sitting.mode)
    try:
        planned = domain.build_slots(
            mode,
            trainee_user_ids=[str(trainee_id) for trainee_id in trainee_ids],
            station_version_ids=[str(station_version_id) for station_version_id in station_version_ids],
        )
    except domain.InvalidCircuit as exc:
        raise_mapped(exc, _REFUSALS)

    values: dict[str, Any] = {}
    if name is not None:
        values["name"] = name
    if supervisor_user_id is not None:
        values["supervisor_user_id"] = supervisor_user_id
    if timing is not None:
        values["timing"] = timing_json(
            domain.normalise_timing(
                {
                    "reading_minutes": timing.reading_minutes,
                    "simulation_minutes": timing.simulation_minutes,
                    "break_minutes": timing.break_minutes,
                    "breaks": [{"after_station": after_station} for after_station in timing.breaks],
                },
                mode=mode,
                station_count=len(station_version_ids),
            )
        )
    if values:
        await repository.update_circuit(session, org_id, circuit_id, **values)
    await repository.bump_circuit_revision(session, org_id, circuit_id)
    await session.refresh(circuit)

    await repository_reads.delete_circuit_structure(session, org_id, circuit_id)
    await repository.add_circuit_members(
        session, circuit_id, trainee_ids=trainee_ids, station_version_ids=station_version_ids
    )
    await repository.create_slots(
        session,
        org_id,
        circuit_id,
        planned=[
            (slot.index, uuid.UUID(slot.trainee_user_id), uuid.UUID(slot.station_version_id))
            for slot in planned
        ],
        room_name=circuit.room_name,
    )
    await service_notify.trainees_scheduled(session, org_id, sitting, trainee_ids)
    await service_notify.reviewer_assigned(session, org_id, sitting, circuit)
    await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.REBUILT)
    return await service.read_circuit(session, org_id, circuit_id)
