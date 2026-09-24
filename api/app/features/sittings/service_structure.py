"""Changing who is on a circuit and what they sit.

Split from `service_circuit.py` along what the two do to a circuit: that module
runs one — starting it, dispatching the agent, ending a consultation — and this
one changes its shape. They are refused for different reasons and at different
moments, which is the seam: appending is allowed *because* a circuit is live
(C8), and rebuilding is refused for the same reason (C3).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_mapped
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
)
from app.features.sittings.models import Circuit, Slot
from app.features.sittings.reads import state as _state
from app.features.sittings.reads import timing_json
from app.features.sittings.schemas import CircuitRead, TimingIn
from app.features.sittings.service import _REFUSALS, _require_circuit, _require_sitting
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
    second would make its slots mean something different. b2b refused the same
    thing and pointed the supervisor at the circuit editor, which is what
    `rebuild_circuit` below is.

    New slots inherit the circuit's live room, which is the point — without it
    a latecomer's slot has no room, and the trainee portal has nothing to
    offer them while a session they are in runs without them.
    """
    circuit = await _require_circuit(session, org_id, circuit_id, lock=True)
    sitting = await _require_sitting(session, org_id, circuit.sitting_id)
    try:
        domain.ensure_live(_state(circuit, has_feedback=False))
        domain.ensure_can_append_trainees(domain.Mode(sitting.mode))
    except (domain.CircuitAlreadyEnded, domain.NotPermittedInMode) as exc:
        raise_mapped(exc, _REFUSALS)

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
    await repository.add_circuit_members(session, circuit_id, trainees=trainee_ids, stations=[])
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
    await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.TRAINEES_APPENDED)
    return await service.read_circuit(session, org_id, circuit_id)


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
) -> CircuitRead:
    """Change who is on a circuit and which stations they sit (C3).

    A structural edit rebuilds the slots, which is why it is refused once any of
    them means something: a consultation in progress would be deleted
    mid-sentence, and recorded feedback would be left pointing at a slot that no
    longer exists. `ensure_editable` is that rule; it had no route to refuse
    anything at, so the only way to correct a circuit was to abandon it and build
    another.
    """
    circuit = await _require_circuit(session, org_id, circuit_id, lock=True)
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
    mode = domain.Mode(sitting.mode)
    try:
        planned = domain.build_slots(
            mode,
            trainees=[str(t) for t in trainee_ids],
            stations=[str(s) for s in station_version_ids],
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
                    "breaks": [{"after_station": b} for b in timing.breaks],
                },
                mode=mode,
                station_count=len(station_version_ids),
            )
        )
    if values:
        await repository.update_circuit(session, org_id, circuit_id, **values)

    await repository_reads.delete_circuit_structure(session, org_id, circuit_id)
    await repository.add_circuit_members(
        session, circuit_id, trainees=trainee_ids, stations=station_version_ids
    )
    await repository.create_slots(
        session,
        org_id,
        circuit_id,
        planned=[(p.index, uuid.UUID(p.trainee), uuid.UUID(p.station)) for p in planned],
        room_name=circuit.room_name,
    )
    await announcements.circuit_changed(session, org_id, circuit_id, name=announcements.REBUILT)
    return await service.read_circuit(session, org_id, circuit_id)
