"""Storage for what the tutor remembers."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.tutor_memory.models import DebriefSummary, LearningEvent, TutorNote


def rows_affected(result: Any) -> int:
    """How many rows a DELETE or UPDATE touched.

    Read off the cursor result, which SQLAlchemy's typed `execute` does not
    promise but every DML statement returns.
    """
    return int(getattr(result, "rowcount", 0) or 0)


async def last_seen_at(
    session: AsyncSession, user_id: uuid.UUID, *, ref_kind: str, ref_id: str
) -> datetime | None:
    """When this person last touched this exact thing, if ever."""
    stmt = (
        select(LearningEvent.occurred_at)
        .where(
            LearningEvent.user_id == user_id,
            LearningEvent.ref_kind == ref_kind,
            LearningEvent.ref_id == ref_id,
        )
        .order_by(desc(LearningEvent.occurred_at))
        .limit(1)
    )
    return (await session.execute(stmt)).scalars().first()


async def add_event(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    exam_id: uuid.UUID | None,
    kind: str,
    ref_kind: str,
    ref_id: str,
    title: str,
    occurred_at: datetime,
    meta: dict[str, Any] | None,
) -> LearningEvent:
    row = LearningEvent(
        user_id=user_id,
        exam_id=exam_id,
        kind=kind,
        ref_kind=ref_kind,
        ref_id=ref_id,
        title=title,
        occurred_at=occurred_at,
        meta=meta,
    )
    session.add(row)
    await session.flush()
    return row


async def recent_events(session: AsyncSession, user_id: uuid.UUID, *, limit: int) -> list[LearningEvent]:
    stmt = (
        select(LearningEvent)
        .where(LearningEvent.user_id == user_id)
        .order_by(desc(LearningEvent.occurred_at))
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars())


async def add_note(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    exam_id: uuid.UUID | None,
    session_id: uuid.UUID | None,
    kind: str,
    body: dict[str, Any],
) -> TutorNote:
    row = TutorNote(user_id=user_id, exam_id=exam_id, session_id=session_id, kind=kind, body=body)
    session.add(row)
    await session.flush()
    return row


async def notes_of_kind(
    session: AsyncSession, user_id: uuid.UUID, *, kind: str, limit: int
) -> list[TutorNote]:
    stmt = (
        select(TutorNote)
        .where(TutorNote.user_id == user_id, TutorNote.kind == kind)
        .order_by(desc(TutorNote.created_at))
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars())


async def note_by_id(session: AsyncSession, note_id: uuid.UUID) -> TutorNote | None:
    return (await session.execute(select(TutorNote).where(TutorNote.id == note_id))).scalar_one_or_none()


async def summary_for_session(session: AsyncSession, session_id: uuid.UUID) -> TutorNote | None:
    stmt = select(TutorNote).where(TutorNote.session_id == session_id, TutorNote.kind == "session_summary")
    return (await session.execute(stmt)).scalars().first()


async def delete_note(session: AsyncSession, user_id: uuid.UUID, note_id: uuid.UUID) -> int:
    """Delete one note of this person's. The user id is in the WHERE clause, not
    checked beforehand: a forget must not be able to reach somebody else's row."""
    result = await session.execute(
        delete(TutorNote).where(TutorNote.id == note_id, TutorNote.user_id == user_id)
    )
    return rows_affected(result)


async def delete_all_for_user(
    session: AsyncSession, user_id: uuid.UUID, *, include_debriefs: bool
) -> dict[str, int]:
    """Forget everything, and say how much was forgotten."""
    counts = {
        "notes": rows_affected(await session.execute(delete(TutorNote).where(TutorNote.user_id == user_id))),
        "events": rows_affected(
            await session.execute(delete(LearningEvent).where(LearningEvent.user_id == user_id))
        ),
        "debrief_summaries": 0,
    }
    if include_debriefs:
        counts["debrief_summaries"] = rows_affected(
            await session.execute(delete(DebriefSummary).where(DebriefSummary.user_id == user_id))
        )
    return counts


async def add_debrief_summary(
    session: AsyncSession,
    *,
    attempt_id: uuid.UUID,
    user_id: uuid.UUID,
    exam_id: uuid.UUID | None,
    key_insights: list[Any],
    action_plan: list[Any],
    narrative: str | None,
    model_used: str | None,
) -> DebriefSummary:
    row = DebriefSummary(
        attempt_id=attempt_id,
        user_id=user_id,
        exam_id=exam_id,
        key_insights=key_insights,
        action_plan=action_plan,
        narrative=narrative,
        model_used=model_used,
    )
    session.add(row)
    await session.flush()
    return row


async def debrief_summary_for_attempt(session: AsyncSession, attempt_id: uuid.UUID) -> DebriefSummary | None:
    stmt = select(DebriefSummary).where(DebriefSummary.attempt_id == attempt_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def set_action_plan(session: AsyncSession, summary_id: uuid.UUID, plan: list[Any]) -> None:
    """Replace one debrief's action plan.

    A whole-column write rather than JSON surgery: the plan is a handful of
    items, read and rewritten inside one transaction.
    """
    await session.execute(
        update(DebriefSummary).where(DebriefSummary.id == summary_id).values(action_plan=plan)
    )


async def recent_debrief_summaries(
    session: AsyncSession, user_id: uuid.UUID, *, limit: int
) -> list[DebriefSummary]:
    stmt = (
        select(DebriefSummary)
        .where(DebriefSummary.user_id == user_id)
        .order_by(desc(DebriefSummary.created_at))
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars())
