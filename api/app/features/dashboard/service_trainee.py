"""The trainee portal's screen: what is happening to me, and can I join it.

Separate from `service.py` (the consumer dashboard) because the person is in a
different product here: this is somebody an institution rosters, looking at a
sitting somebody else is running.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import service_reads as attempts
from app.features.dashboard.schemas import MySitting, MySittings, MySlot
from app.features.results import service_candidate as results
from app.features.sittings import service_reads as sittings
from app.features.stations import service_reads as stations

# A slot is finished for the candidate once the station is completed or the
# circuit moved past it.
FINISHED_STATUSES = frozenset({"completed", "abandoned", "expired", "skipped"})


def _joinable(status: str, room_name: str | None, exam_completed: bool, circuit_live: bool) -> bool:
    return bool(room_name) and circuit_live and not exam_completed and status not in FINISHED_STATUSES


async def my_sittings(
    session: AsyncSession, user_id: uuid.UUID, *, org_slugs: Mapping[uuid.UUID, str], now: datetime
) -> MySittings:
    """Every sitting this person is rostered onto, grouped by circuit.

    Grouped by circuit rather than by sitting because a circuit is what a
    trainee is actually in: two circuits of one sitting run separately, in
    different rooms, and can be at different stations.

    `org_slugs` comes from the caller's token rather than another query — the
    memberships are already in the JWT, and a slug is display, not access.
    """
    trainee_slots = await sittings.slots_for_trainee(session, user_id)
    titles = await _titles_per_org(session, trainee_slots)
    live = await attempts.live_attempts_for_slots(
        session, [trainee_slot.slot.id for trainee_slot in trainee_slots]
    )
    sealed = await _sealed_sittings(session, trainee_slots, user_id)

    grouped: dict[uuid.UUID, MySitting] = {}
    for trainee_slot in trainee_slots:
        entry = grouped.get(trainee_slot.circuit.id)
        if entry is None:
            entry = MySitting(
                id=trainee_slot.sitting.id,
                name=trainee_slot.sitting.name,
                mode=trainee_slot.sitting.mode,
                status=trainee_slot.sitting.status,
                scheduled_for=trainee_slot.sitting.scheduled_for,
                org_id=trainee_slot.sitting.org_id,
                org_slug=org_slugs.get(trainee_slot.sitting.org_id),
                circuit_id=trainee_slot.circuit.id,
                circuit_name=trainee_slot.circuit.name,
                live=_circuit_live(trainee_slot.circuit),
                can_join=_circuit_live(trainee_slot.circuit) and bool(trainee_slot.circuit.room_name),
                phase=trainee_slot.circuit.phase,
                phase_started_at=trainee_slot.circuit.phase_started_at,
                phase_ends_at=trainee_slot.circuit.phase_ends_at,
                paused=trainee_slot.circuit.paused_at is not None,
                remaining_seconds=sittings.remaining_seconds(
                    trainee_slot.circuit.phase_ends_at, paused_at=trainee_slot.circuit.paused_at, now=now
                ),
                active_slot_id=trainee_slot.circuit.active_slot_id,
                slots=[],
            )
            grouped[trainee_slot.circuit.id] = entry

        circuit_live = _circuit_live(trainee_slot.circuit)
        is_active = trainee_slot.circuit.active_slot_id == trainee_slot.slot.id
        summary = titles.get(trainee_slot.slot.station_version_id)
        entry.slots.append(
            MySlot(
                id=trainee_slot.slot.id,
                slot_index=trainee_slot.slot.slot_index,
                status=trainee_slot.slot.status,
                room_name=trainee_slot.slot.room_name,
                station_title=summary.title if summary else None,
                station_id=summary.station_id if summary else None,
                station_version_id=trainee_slot.slot.station_version_id,
                started_at=trainee_slot.slot.started_at,
                ended_at=trainee_slot.slot.ended_at,
                exam_completed_at=trainee_slot.slot.exam_completed_at,
                joinable=_joinable(
                    trainee_slot.slot.status,
                    trainee_slot.slot.room_name,
                    trainee_slot.slot.exam_completed_at is not None,
                    circuit_live,
                ),
                attempt_id=live[trainee_slot.slot.id].id
                if trainee_slot.slot.id in live and trainee_slot.sitting.id not in sealed
                else None,
                is_active=is_active,
                phase=trainee_slot.circuit.phase if is_active else None,
                phase_started_at=trainee_slot.circuit.phase_started_at if is_active else None,
                phase_ends_at=trainee_slot.circuit.phase_ends_at if is_active else None,
            )
        )
    return MySittings(items=list(grouped.values()))


async def _sealed_sittings(
    session: AsyncSession, trainee_slots: list[sittings.TraineeSlot], user_id: uuid.UUID
) -> set[uuid.UUID]:
    """Exam sittings whose result is not yet released to this person.

    Their attempts are not linked: the transcript and marks are refused until
    release (`attempts.service_access`), so a link would only lead to a refusal (R-1).
    """
    exam_sittings = {slot.sitting.id for slot in trainee_slots if slot.sitting.mode == "exam"}
    return {
        sitting_id
        for sitting_id in exam_sittings
        if await results.released_revision_for_user(session, sitting_id, user_id) is None
    }


def _circuit_live(circuit: sittings.CircuitRef) -> bool:
    return circuit.started_at is not None and circuit.ended_at is None


async def _titles_per_org(
    session: AsyncSession, trainee_slots: list[sittings.TraineeSlot]
) -> dict[uuid.UUID, stations.StationSummary]:
    """Station titles, asked for once per organisation.

    Scoped per org because a circuit may run that org's own stations as well as
    the platform library, and a station version is readable only by the org
    that owns it. One query per organisation, not one per slot.
    """
    by_org: dict[uuid.UUID, list[uuid.UUID]] = {}
    for trainee_slot in trainee_slots:
        by_org.setdefault(trainee_slot.sitting.org_id, []).append(trainee_slot.slot.station_version_id)

    found: dict[uuid.UUID, stations.StationSummary] = {}
    for org_id, version_ids in by_org.items():
        found.update(await stations.summaries_by_version_id(session, org_id, version_ids))
    return found
