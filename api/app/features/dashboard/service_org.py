"""Assembling the institutional screens.

Reads through other slices' services, never their tables, so this stays a projection.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import service as catalog
from app.features.dashboard.schemas_org import (
    OrgCounts,
    OrgDashboard,
    OrgSetup,
    OrgSittingRow,
    SupervisorCircuitRow,
    SupervisorCircuits,
)
from app.features.roster import service as roster
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
    # The library an org may draw on is the library of the exams it offers, so
    # this is one lookup feeding two counts.
    exam_ids = await catalog.org_exam_ids(session, org_id)
    counts = OrgCounts(
        trainees=await roster.count_trainees(session, org_id),
        stations=await stations.count_stations(session, org_id),
        library_stations=await stations.count_library_stations(session, exam_ids),
        staff=await memberships.count_staff(session, org_id),
        programmes_with_markable_exam=await catalog.count_programmes_with_markable_exam(session, org_id),
        sittings=await sittings.count_sittings(session, org_id),
    )
    # A station is *available* if this organisation wrote it or the platform
    # published it for an exam the organisation runs. Only the first used to
    # count, so a catalogue-only institution was told to keep setting up while
    # it was already running examinations.
    stations_available = counts.stations > 0 or counts.library_stations > 0
    setup = OrgSetup(
        trainees_added=counts.trainees > 0,
        stations_available=stations_available,
        team_invited=counts.staff > 0,
        programme_exam_rubric_ready=counts.programmes_with_markable_exam > 0,
        ready_to_run=(
            counts.trainees > 0
            and stations_available
            and counts.staff > 0
            and counts.programmes_with_markable_exam > 0
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
                id=sitting.id,
                name=sitting.name,
                mode=sitting.mode,
                status=sitting.status,
                scheduled_for=sitting.scheduled_for,
            )
            for sitting in recent
        ],
    )


async def supervisor_circuits(
    session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID
) -> SupervisorCircuits:
    """The circuits assigned to the caller: "your sessions", in one request."""
    circuits = await sittings.supervisor_circuits(session, org_id, user_id)
    return SupervisorCircuits(
        items=[
            SupervisorCircuitRow(
                circuit_id=circuit.circuit.id,
                circuit_name=circuit.circuit.name,
                sitting_id=circuit.sitting.id,
                sitting_name=circuit.sitting.name,
                mode=circuit.sitting.mode,
                status=circuit.sitting.status,
                scheduled_for=circuit.sitting.scheduled_for,
                slot_count=circuit.slot_count,
                in_progress=circuit.circuit.started_at is not None and circuit.circuit.ended_at is None,
                ended=circuit.circuit.ended_at is not None,
            )
            for circuit in circuits
        ]
    )
