"""Choose a library station for a peer practice session."""

from __future__ import annotations

import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.stations.repository_library import published_library_versions


async def pick_station_version_id(
    session: AsyncSession, *, exam_id: uuid.UUID, doctor_user_id: uuid.UUID
) -> uuid.UUID | None:
    """Pick a published platform-library station for this exam.

    Mirrors b2c's intent: random among published stations. Preferring
    unattempted stations would need attempt history keyed to practice sessions;
    the library pick is enough for a fair session.
    """
    candidates = await published_library_versions(session, exam_id=exam_id)
    if not candidates:
        return None
    version, _station = random.choice(candidates)
    return version.id
