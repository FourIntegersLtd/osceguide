"""Choose a library station for a peer practice session."""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.stations import service_reads as stations


async def pick_station_version_id(
    session: AsyncSession, *, exam_id: uuid.UUID, doctor_user_id: uuid.UUID
) -> uuid.UUID | None:
    """Pick a published platform-library station for this exam, at random.

    Scoped to the doctor's own plan window: a session must never hand a limited learner a station
    their plan does not unlock. Preferring unattempted stations would need attempt history keyed to
    practice sessions; the library pick is enough for a fair session.
    """
    candidates = await stations.allowed_published_library_version_ids(
        session, exam_id=exam_id, user_id=doctor_user_id, now=datetime.now(UTC)
    )
    if not candidates:
        return None
    return random.choice(candidates)  # noqa: S311 — fairness pick, not a security decision
