"""Looking something up in this doctor's own past.

Separate from `service_material.py`, which searches the shared catalogue by meaning: a
person's history is small and retrieved by the words they used instead. Every read here
takes a `user_id`, which is what keeps one doctor's history out of another's conversation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.tutor_memory import domain, repository
from app.features.tutor_memory.schemas import ToolResult

NOTHING_FOUND = "You have nothing on file about that. Say so plainly rather than guessing."


async def recall(
    session: AsyncSession, *, user_id: uuid.UUID, query: str, kind: str, limit: int, now: datetime
) -> ToolResult:
    """Search this person's own past by the words they used.

    Substring matching rather than a search index: a doctor has tens of these, not
    thousands.
    """
    lines: list[str] = []
    needle = query.lower()

    if kind in {"note", "any"}:
        for note in await repository.notes_of_kind(session, user_id, kind="stated_fact", limit=20):
            fact = str((note.body or {}).get("fact") or "")
            if needle in fact.lower():
                lines.append(f"They told you: {fact}")

    if kind in {"debrief", "consultation", "any"}:
        for row in await repository.recent_debrief_summaries(session, user_id, limit=20):
            haystack = " ".join(
                [str(row.narrative or ""), *[str(i) for i in (row.key_insights or [])]]
            ).lower()
            if needle not in haystack:
                continue
            steps = domain.open_action_items([row.action_plan or []])
            when = domain.days_ago(row.created_at, now)
            agreed = f" You agreed they would: {'; '.join(steps)}." if steps else ""
            lines.append(f"A debrief {when} days ago: {row.narrative or 'no narrative'}.{agreed}")

    if kind in {"activity", "any"}:
        for event in await repository.recent_events(session, user_id, limit=40):
            if needle in event.title.lower():
                lines.append(
                    f"They {event.kind} {event.title}, {domain.days_ago(event.occurred_at, now)} days ago."
                )

    if not lines:
        return ToolResult(result=NOTHING_FOUND)
    return ToolResult(result=" ".join(lines[:limit]))
