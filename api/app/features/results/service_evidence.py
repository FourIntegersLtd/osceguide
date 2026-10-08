"""What a candidate's decision is judged against, read from the marking itself (R-25).

The client used to send this and the server fingerprinted whatever arrived, so a
release could present the signed-off evidence regardless of what the stations
now said. The shape is the one the screen has always built: per station whether
it is marked and its rating, the count marked, and the worst rating overall.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import service_reads as attempts
from app.features.reviews import service_summary as reviews
from app.features.rubrics import service_marking as rubrics
from app.features.rubrics import service_scoring as scoring
from app.features.sittings import service_reads as sittings


async def current_evidence(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID, user_id: uuid.UUID | None
) -> dict[str, Any]:
    """The candidate's stations in this sitting as they are marked right now."""
    sitting = await sittings.sitting_ref(session, org_id, sitting_id)
    slots = [
        slot
        for slot in await sittings.slots_for_sitting(session, org_id, sitting_id)
        if user_id is not None and slot.trainee_id == user_id
    ]
    slot_ids = [slot.id for slot in slots]
    live = await attempts.live_attempts_for_slots(session, slot_ids)
    summaries = await reviews.summaries_for_slots(session, org_id, slot_ids)
    stations = sorted(
        (
            {
                "slot_id": str(slot.id),
                "marked": slot.id in live and live[slot.id].status == "evaluated",
                "overall_rag": summaries[slot.id].overall_rag,
            }
            for slot in slots
        ),
        key=lambda station: str(station["slot_id"]),
    )
    overall = None
    if sitting is not None:
        rubric = await rubrics.scoring_rubric_for_version(session, org_id, sitting.rubric_version_id)
        overall = scoring.worst_rating(rubric.structure, [station["overall_rag"] for station in stations])
    return {
        "stations": stations,
        "stations_marked": sum(1 for station in stations if station["marked"]),
        "overall_rag": overall,
    }
