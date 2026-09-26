"""Recording what somebody did, showing them what is remembered, and forgetting it.

The learner-facing half of the slice. The tutor-facing half — composing the
brief, answering tool calls, writing summaries — lives in the `service_*`
modules beside this one.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorParams, Page
from app.features.assistant import service as assistant
from app.features.attempts.service_debrief import debrief_sources
from app.features.catalog import service as catalog
from app.features.tutor_memory import domain, errors, repository
from app.features.tutor_memory.schemas import (
    ActivityAccepted,
    ActivityIn,
    DebriefSummaryRead,
    EventRead,
    ForgottenCounts,
    NoteRead,
    ToolResult,
    TutorMemoryRead,
)

MAX_NOTES = 40
MAX_EVENTS = 60
MAX_DEBRIEFS = 20


async def record_activity(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    events: list[ActivityIn],
    now: datetime,
) -> ActivityAccepted:
    """Write down what this person read, practised or listened to.

    A repeat inside the dedup window is accepted but not recorded. A malformed event is
    dropped rather than failing the whole batch, since these arrive from a browser as it
    goes, often as a tab is closing.
    """
    recorded = 0
    for event in events:
        if event.kind not in domain.EVENT_KINDS or event.ref_kind not in domain.REF_KINDS:
            continue
        occurred_at = event.occurred_at or now
        last = await repository.last_seen_at(session, user_id, ref_kind=event.ref_kind, ref_id=event.ref_id)
        if not domain.should_record_event(last_seen_at=last, now=occurred_at):
            continue
        await repository.add_event(
            session,
            user_id=user_id,
            exam_id=await _exam_id(session, event.exam_code),
            kind=event.kind,
            ref_kind=event.ref_kind,
            ref_id=event.ref_id,
            title=event.title,
            occurred_at=occurred_at,
            meta=event.meta,
        )
        recorded += 1
    return ActivityAccepted(accepted=len(events), recorded=recorded)


async def run_tool(
    session: AsyncSession,
    *,
    session_id: uuid.UUID,
    tool: str,
    arguments: dict[str, Any],
    now: datetime,
) -> ToolResult:
    """One tool call, checked by `assistant` and answered here.

    Routed through `assistant`, which owns whose session this is and whether it is still
    running; what the tool means is ours.
    """
    return ToolResult(
        **await assistant.run_tool(session, session_id, tool=tool, arguments=arguments, now=now)
    )


async def read_memory(session: AsyncSession, user_id: uuid.UUID) -> TutorMemoryRead:
    """Everything on file about this person, as they may read it. The tutor speaks from this."""
    notes = await repository.notes_of_kind(session, user_id, kind="session_summary", limit=MAX_NOTES)
    notes += await repository.notes_of_kind(session, user_id, kind="stated_fact", limit=MAX_NOTES)
    notes.sort(key=lambda note: note.created_at, reverse=True)
    events = await repository.recent_events(session, user_id, limit=MAX_EVENTS)
    debriefs = await repository.recent_debrief_summaries(session, user_id, limit=MAX_DEBRIEFS)
    sources = await debrief_sources(session, user_id, [debrief.attempt_id for debrief in debriefs])

    return TutorMemoryRead(
        notes=[
            NoteRead(id=note.id, kind=note.kind, body=dict(note.body or {}), created_at=note.created_at)
            for note in notes[:MAX_NOTES]
        ],
        events=[
            EventRead(
                id=event.id,
                kind=event.kind,
                ref_kind=event.ref_kind,
                ref_id=event.ref_id,
                title=event.title,
                occurred_at=event.occurred_at,
            )
            for event in events
        ],
        debrief_summaries=[
            DebriefSummaryRead(
                id=debrief.id,
                attempt_id=debrief.attempt_id,
                source_attempt_id=sources.get(debrief.attempt_id),
                key_insights=list(debrief.key_insights or []),
                action_plan=list(debrief.action_plan or []),
                narrative=debrief.narrative,
                created_at=debrief.created_at,
            )
            for debrief in debriefs
        ],
    )


async def forget_note(session: AsyncSession, *, user_id: uuid.UUID, note_id: uuid.UUID) -> None:
    """Delete one note. Somebody else's note is a 404, not a 403: saying "that
    exists but is not yours" about a private note tells them it exists."""
    if not await repository.delete_note(session, user_id, note_id):
        raise errors.NoteNotFound()


async def forget_everything(
    session: AsyncSession, *, user_id: uuid.UUID, include_debriefs: bool
) -> ForgottenCounts:
    """Forget the lot, and say how much was forgotten.

    Debrief summaries are opt-in: they are also the doctor's own record of what a debrief
    concluded, shown on their results.
    """
    counts = await repository.delete_all_for_user(session, user_id, include_debriefs=include_debriefs)
    return ForgottenCounts(**counts)


async def _exam_id(session: AsyncSession, exam_code: str | None) -> uuid.UUID | None:
    """Resolve an exam code, or record the event without one if it names nothing."""
    if not exam_code:
        return None
    for ref in await catalog.exam_refs(session):
        if ref.code == exam_code:
            return ref.id
    return None


# --- The learner's complete debrief history, not the tutor's recent-memory window.


async def list_debriefs(
    session: AsyncSession, user_id: uuid.UUID, params: CursorParams
) -> Page[DebriefSummaryRead]:
    debriefs, cursor = await repository.page_debrief_summaries(session, user_id, params)
    sources = await debrief_sources(session, user_id, [debrief.attempt_id for debrief in debriefs])
    return Page(
        items=[
            DebriefSummaryRead(
                id=debrief.id,
                attempt_id=debrief.attempt_id,
                source_attempt_id=sources.get(debrief.attempt_id),
                key_insights=list(debrief.key_insights or []),
                action_plan=list(debrief.action_plan or []),
                narrative=debrief.narrative,
                created_at=debrief.created_at,
            )
            for debrief in debriefs
        ],
        next_cursor=cursor,
    )
