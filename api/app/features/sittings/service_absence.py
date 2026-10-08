"""A person leaving the organisation mid-schedule: what that does to stations still to come."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sittings import repository_run


async def skip_unstarted_stations(
    session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, *, now: datetime
) -> int:
    """S-18: end this person's unstarted stations as absent results (`skipped`).

    A station already under way is left to finish; the running circuit's clock carries on.
    """
    return await repository_run.skip_unstarted_slots_for_user(session, org_id, user_id, now=now)
