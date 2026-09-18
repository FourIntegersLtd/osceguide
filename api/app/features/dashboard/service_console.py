"""The supervisor's console: one request for the screen an examination is run from.

Split from `service_org.py` at the file cap, along the line that was already
there: the organisation's own screens change when an admin needs a different
number, and this changes when running an examination works differently.

It is assembled from six slices here so it is assembled once, rather than by a
browser making a request per slot for the station title, a request per slot for
whether it has been marked, and the whole thing again every eight seconds.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import service_reads as attempts
from app.features.dashboard.errors import CircuitNotFound
from app.features.dashboard.schemas_org import (
    CircuitConsole,
    ConsoleCircuit,
    ConsolePerson,
    ConsoleSitting,
    ConsoleSlot,
    ConsoleStation,
    ConsoleTiming,
)
from app.features.identity import service as identity
from app.features.reviews import service as reviews
from app.features.roster import service as roster
from app.features.sittings import service_circuit
from app.features.sittings import service_reads as sittings
from app.features.stations import service_reads as stations


async def build_console(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, *, now: datetime
) -> CircuitConsole:
    """Everything the supervisor's screen shows, in one request.

    It is assembled from five slices here so it is assembled once, rather than
    by a browser making a request per slot for the station title, a request per
    slot for whether it has been marked, and the whole thing again every eight
    seconds.
    """
    detail = await sittings.circuit_detail(session, org_id, circuit_id)
    if detail is None:
        raise CircuitNotFound()

    slot_ids = [slot.id for slot in detail.slots]
    user_ids = [slot.trainee_id for slot in detail.slots]
    if detail.circuit.supervisor_user_id is not None:
        user_ids.append(detail.circuit.supervisor_user_id)

    people = await identity.user_refs_by_ids(session, user_ids)
    trainees = await roster.trainees_by_user_id(session, org_id, user_ids)
    station_summaries = await stations.summaries_by_version_id(
        session, org_id, [slot.station_version_id for slot in detail.slots]
    )
    reviewed = await reviews.reviewed_slot_ids(session, slot_ids)
    live = await attempts.live_attempts_for_slots(session, slot_ids)
    lock = await service_circuit.read_edit_lock(session, org_id, circuit_id)

    def person(user_id: uuid.UUID) -> ConsolePerson:
        ref = people.get(user_id)
        trainee = trainees.get(user_id)
        return ConsolePerson(
            user_id=user_id,
            name=ref.name if ref else None,
            email=ref.email if ref else None,
            trainee_id=trainee.id if trainee else None,
        )

    circuit = ConsoleCircuit(
        id=detail.circuit.id,
        name=detail.circuit.name,
        timing=ConsoleTiming(
            reading_minutes=detail.circuit.timing.reading_minutes,
            simulation_minutes=detail.circuit.timing.simulation_minutes,
            break_minutes=detail.circuit.timing.break_minutes,
            breaks=list(detail.circuit.timing.breaks),
        ),
        active_slot_id=detail.circuit.active_slot_id,
        room_name=detail.circuit.room_name,
        started_at=detail.circuit.started_at,
        ended_at=detail.circuit.ended_at,
        agent_dispatched=detail.circuit.agent_dispatched_at is not None,
        supervisor=(
            person(detail.circuit.supervisor_user_id)
            if detail.circuit.supervisor_user_id is not None
            else None
        ),
        editable=lock.editable,
        edit_block=lock.reason,
        phase=detail.circuit.phase,
        phase_started_at=detail.circuit.phase_started_at,
        phase_ends_at=detail.circuit.phase_ends_at,
        phase_seq=detail.circuit.phase_seq,
        paused=detail.circuit.paused_at is not None,
        paused_at=detail.circuit.paused_at,
        auto_advance=detail.circuit.auto_advance,
        elapsed_seconds=sittings.elapsed_seconds(
            detail.circuit.phase_started_at,
            paused_seconds=detail.circuit.paused_seconds,
            paused_at=detail.circuit.paused_at,
            now=now,
        ),
        remaining_seconds=sittings.remaining_seconds(
            detail.circuit.phase_ends_at, paused_at=detail.circuit.paused_at, now=now
        ),
        alerts=sittings.alerts_for(
            phase=detail.circuit.phase,
            phase_started_at=detail.circuit.phase_started_at,
            phase_ends_at=detail.circuit.phase_ends_at,
            paused_at=detail.circuit.paused_at,
            attempt_status=_active_attempt_status(detail, live),
            now=now,
        ),
    )
    return CircuitConsole(
        sitting=ConsoleSitting(
            id=detail.sitting.id,
            name=detail.sitting.name,
            mode=detail.sitting.mode,
            sitting_type=detail.sitting.sitting_type,
            status=detail.sitting.status,
            scheduled_for=detail.sitting.scheduled_for,
            feedback_template_version_id=detail.sitting.feedback_template_version_id,
        ),
        circuit=circuit,
        slots=[
            ConsoleSlot(
                id=slot.id,
                slot_index=slot.slot_index,
                status=slot.status,
                room_name=slot.room_name,
                started_at=slot.started_at,
                ended_at=slot.ended_at,
                exam_completed_at=slot.exam_completed_at,
                trainee=person(slot.trainee_id),
                station=_station(slot.station_version_id, station_summaries),
                has_review=slot.id in reviewed,
                is_active=detail.circuit.active_slot_id == slot.id,
                attempt_id=live[slot.id].id if slot.id in live else None,
                # Derived from the circuit: the clock is the circuit's, and
                # only the slot it is on is in a phase.
                phase=_phase_for(detail, slot.id),
                phase_started_at=_when(detail, slot.id, detail.circuit.phase_started_at),
                phase_ends_at=_when(detail, slot.id, detail.circuit.phase_ends_at),
            )
            for slot in detail.slots
        ],
    )


def _phase_for(detail: sittings.CircuitDetail, slot_id: uuid.UUID) -> str | None:
    return detail.circuit.phase if detail.circuit.active_slot_id == slot_id else None


def _when(detail: sittings.CircuitDetail, slot_id: uuid.UUID, value: datetime | None) -> datetime | None:
    return value if detail.circuit.active_slot_id == slot_id else None


def _active_attempt_status(
    detail: sittings.CircuitDetail, live: dict[uuid.UUID, attempts.AttemptRef]
) -> str | None:
    """The recording of the station in progress, if there is one.

    What the "no patient in the room" alert is decided from: a consultation
    running with nothing recording it is the failure that used to be noticed by
    a supervisor watching a silent room.
    """
    slot_id = detail.circuit.active_slot_id
    if slot_id is None or slot_id not in live:
        return None
    return live[slot_id].status


def _station(version_id: uuid.UUID, summaries: dict[uuid.UUID, stations.StationSummary]) -> ConsoleStation:
    found = summaries.get(version_id)
    if found is None:
        return ConsoleStation(version_id=version_id)
    return ConsoleStation(
        version_id=version_id,
        station_id=found.station_id,
        title=found.title,
        version=found.version,
        status=found.status,
    )
