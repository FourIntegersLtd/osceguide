"""The trainee portal's screen: what is happening to me, and can I join it.

Separate from `service.py` (the consumer dashboard) because the person is in a
different product here: this is somebody an institution rosters, looking at a
sitting somebody else is running.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import service_reads as attempts
from app.features.dashboard.schemas import MySitting, MySittings, MySlot
from app.features.sittings import service_reads as sittings
from app.features.stations import service_reads as stations

# A slot is finished for the candidate once the station is completed, however
# the circuit ends up. b2b decides this in the browser by string-matching the
# status, which is why a completed station kept offering a "join" button.
FINISHED_STATUSES = frozenset({"completed", "abandoned", "expired"})


def _joinable(status: str, room_name: str | None, exam_completed: bool, circuit_live: bool) -> bool:
    return bool(room_name) and circuit_live and not exam_completed and status not in FINISHED_STATUSES


async def my_sittings(
    session: AsyncSession, user_id: uuid.UUID, *, org_slugs: Mapping[uuid.UUID, str]
) -> MySittings:
    """Every sitting this person is rostered onto, grouped by circuit.

    Grouped by circuit rather than by sitting because a circuit is what a
    trainee is actually in: two circuits of one sitting run separately, in
    different rooms, and can be at different stations.

    `org_slugs` comes from the caller's token rather than another query — the
    memberships are already in the JWT, and a slug is display, not access.
    """
    rows = await sittings.slots_for_trainee(session, user_id)
    titles = await _titles_per_org(session, rows)
    live = await attempts.live_attempts_for_slots(session, [row.slot.id for row in rows])

    grouped: dict[uuid.UUID, MySitting] = {}
    for row in rows:
        entry = grouped.get(row.circuit.id)
        if entry is None:
            entry = MySitting(
                id=row.sitting.id,
                name=row.sitting.name,
                mode=row.sitting.mode,
                status=row.sitting.status,
                scheduled_for=row.sitting.scheduled_for,
                org_id=row.sitting.org_id,
                org_slug=org_slugs.get(row.sitting.org_id),
                circuit_id=row.circuit.id,
                circuit_name=row.circuit.name,
                slots=[],
            )
            grouped[row.circuit.id] = entry

        circuit_live = row.circuit.started_at is not None and row.circuit.ended_at is None
        summary = titles.get(row.slot.station_version_id)
        entry.slots.append(
            MySlot(
                id=row.slot.id,
                slot_index=row.slot.slot_index,
                status=row.slot.status,
                room_name=row.slot.room_name,
                station_title=summary.title if summary else None,
                started_at=row.slot.started_at,
                ended_at=row.slot.ended_at,
                exam_completed_at=row.slot.exam_completed_at,
                joinable=_joinable(
                    row.slot.status,
                    row.slot.room_name,
                    row.slot.exam_completed_at is not None,
                    circuit_live,
                ),
                attempt_id=live[row.slot.id].id if row.slot.id in live else None,
                phase=row.slot.phase,
                phase_started_at=row.slot.phase_started_at,
                phase_ends_at=row.slot.phase_ends_at,
            )
        )
    return MySittings(items=list(grouped.values()))


async def _titles_per_org(
    session: AsyncSession, rows: list[sittings.TraineeSlot]
) -> dict[uuid.UUID, stations.StationSummary]:
    """Station titles, asked for once per organisation.

    Scoped per org because a circuit may run that org's own stations as well as
    the platform library, and a station version is readable only by the org
    that owns it. One query per organisation, not one per slot.
    """
    by_org: dict[uuid.UUID, list[uuid.UUID]] = {}
    for row in rows:
        by_org.setdefault(row.sitting.org_id, []).append(row.slot.station_version_id)

    found: dict[uuid.UUID, stations.StationSummary] = {}
    for org_id, version_ids in by_org.items():
        found.update(await stations.summaries_by_version_id(session, org_id, version_ids))
    return found
