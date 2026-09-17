"""Assembling the institutional screens.

Reads through other slices' services, never their tables, so this stays a
projection. Split from `service.py` because the learner's dashboard and an
organisation's change for different reasons and share nothing but the idea.
"""

from __future__ import annotations

import uuid

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
    OrgCounts,
    OrgDashboard,
    OrgSetup,
    OrgSittingRow,
    SupervisorCircuitRow,
    SupervisorCircuits,
)
from app.features.identity import service as identity
from app.features.reviews import service as reviews
from app.features.roster import service as roster
from app.features.rubrics import service_feedback as rubrics
from app.features.sittings import service_circuit
from app.features.sittings import service_reads as sittings
from app.features.stations import service_reads as stations
from app.features.tenancy import service as tenancy
from app.features.tenancy import service_memberships as memberships

RECENT_SITTINGS = 10


async def build_org_dashboard(session: AsyncSession, org_id: uuid.UUID) -> OrgDashboard:
    """The admin home screen, which currently makes five requests.

    Four of those exist only to call `.length` on a list, which also means an
    organisation with a thousand trainees downloads a thousand trainees to show
    the number 1000.
    """
    org = await tenancy.read_organization(session, org_id)
    counts = OrgCounts(
        trainees=await roster.count_trainees(session, org_id),
        stations=await stations.count_stations(session, org_id),
        staff=await memberships.count_staff(session, org_id),
        published_feedback_templates=await rubrics.count_published_versions(session, org_id),
        sittings=await sittings.count_sittings(session, org_id),
    )
    setup = OrgSetup(
        trainees_added=counts.trainees > 0,
        stations_authored=counts.stations > 0,
        team_invited=counts.staff > 0,
        feedback_template_published=counts.published_feedback_templates > 0,
        ready_to_run=(
            counts.trainees > 0
            and counts.stations > 0
            and counts.staff > 0
            and counts.published_feedback_templates > 0
        ),
    )
    recent = await sittings.recent_sittings(session, org_id, limit=RECENT_SITTINGS)
    return OrgDashboard(
        org_id=org.id,
        slug=org.slug,
        name=org.name,
        counts=counts,
        setup=setup,
        recent_sittings=[
            OrgSittingRow(
                id=row.id,
                name=row.name,
                mode=row.mode,
                status=row.status,
                scheduled_for=row.scheduled_for,
            )
            for row in recent
        ],
    )


async def supervisor_circuits(
    session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID
) -> SupervisorCircuits:
    """The circuits assigned to the caller: "your sessions", in one request."""
    rows = await sittings.supervisor_circuits(session, org_id, user_id)
    return SupervisorCircuits(
        items=[
            SupervisorCircuitRow(
                circuit_id=row.circuit.id,
                circuit_name=row.circuit.name,
                sitting_id=row.sitting.id,
                sitting_name=row.sitting.name,
                mode=row.sitting.mode,
                status=row.sitting.status,
                scheduled_for=row.sitting.scheduled_for,
                slot_count=row.slot_count,
                in_progress=row.circuit.started_at is not None and row.circuit.ended_at is None,
                ended=row.circuit.ended_at is not None,
            )
            for row in rows
        ]
    )


async def build_console(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> CircuitConsole:
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
                phase=slot.phase,
                phase_started_at=slot.phase_started_at,
                phase_ends_at=slot.phase_ends_at,
            )
            for slot in detail.slots
        ],
    )


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
