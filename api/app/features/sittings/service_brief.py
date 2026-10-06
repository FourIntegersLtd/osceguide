"""What a candidate reads during a station's reading time.

Keyed on the slot, not on the attempt: the circuit's attempt is created when the
patient is dispatched, after reading, so an attempt-keyed read had nothing to show
while the candidate was reading. One read for every station source — the org's own
and the platform library's — because the circuit runs both.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sittings import errors
from app.features.sittings.schemas import SlotBriefRead
from app.features.sittings.service import slot_and_circuit_for_owner
from app.features.stations import service as stations


async def brief_for_trainee(
    session: AsyncSession, slot_id: uuid.UUID, *, user_id: uuid.UUID
) -> SlotBriefRead:
    """The brief, once the circuit has reached this candidate's slot.

    Not before: a brief readable from the roster would be a station read the
    night before the examination.
    """
    found = await slot_and_circuit_for_owner(session, slot_id, user_id)
    if found is None:
        # 404, not 403: whether a slot exists is not something to confirm to somebody it is not for.
        raise errors.SlotNotFound()
    slot, circuit = found
    if circuit.started_at is None or (circuit.active_slot_id != slot.id and slot.started_at is None):
        raise errors.CircuitNotStarted()
    brief = await stations.reading_brief(session, slot.org_id, slot.station_version_id)
    if brief is None:
        raise errors.SlotNotFound()
    return SlotBriefRead(slot_id=slot.id, station_title=brief.title, sections=brief.sections, text=brief.text)
