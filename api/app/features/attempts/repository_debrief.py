"""Source consultations for a learner's debrief summaries."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import Attempt


async def sources_for(
    session: AsyncSession,
    user_id: uuid.UUID,
    attempt_ids: list[uuid.UUID],
) -> dict[uuid.UUID, uuid.UUID]:
    rows = await session.execute(
        select(Attempt.id, Attempt.source_attempt_id).where(
            Attempt.user_id == user_id,
            Attempt.id.in_(attempt_ids),
            Attempt.kind == "debrief",
            Attempt.source_attempt_id.is_not(None),
        )
    )
    return {attempt_id: source_id for attempt_id, source_id in rows.all() if source_id is not None}
