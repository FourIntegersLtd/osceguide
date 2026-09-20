"""The learner's complete debrief history, not the tutor's recent-memory window."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorParams, Page
from app.features.attempts.service_debrief import debrief_sources
from app.features.tutor_memory import repository
from app.features.tutor_memory.schemas import DebriefSummaryRead


async def list_debriefs(
    session: AsyncSession, user_id: uuid.UUID, params: CursorParams
) -> Page[DebriefSummaryRead]:
    rows, cursor = await repository.page_debrief_summaries(session, user_id, params)
    sources = await debrief_sources(session, user_id, [row.attempt_id for row in rows])
    return Page(
        items=[
            DebriefSummaryRead(
                id=row.id,
                attempt_id=row.attempt_id,
                source_attempt_id=sources.get(row.attempt_id),
                key_insights=list(row.key_insights or []),
                action_plan=list(row.action_plan or []),
                narrative=row.narrative,
                created_at=row.created_at,
            )
            for row in rows
        ],
        next_cursor=cursor,
    )
