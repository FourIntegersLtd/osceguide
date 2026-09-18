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

from app.features.assistant import service as assistant
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

    A repeat inside the dedup window is accepted and not recorded: somebody who
    opens a summary, follows a link and comes back has read it once, and a
    memory that says twice will be spoken back to them as a pattern.

    A malformed event is dropped rather than failing the batch. These arrive
    from a browser as it goes, often as a tab is closing, and refusing the
    whole batch over one bad row would lose the good ones with it.
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

    Routed through `assistant` rather than straight to `service_tools` so the
    two questions stay where they belong: whose session this is and whether it
    is still running is `assistant`'s, and what the tool means is ours.
    """
    return ToolResult(
        **await assistant.run_tool(session, session_id, tool=tool, arguments=arguments, now=now)
    )


async def read_memory(session: AsyncSession, user_id: uuid.UUID) -> TutorMemoryRead:
    """Everything on file about this person, as they may read it.

    The tutor speaks from this; a memory nobody can inspect is one nobody can
    correct, which is why the route exists at all.
    """
    notes = await repository.notes_of_kind(session, user_id, kind="session_summary", limit=MAX_NOTES)
    notes += await repository.notes_of_kind(session, user_id, kind="stated_fact", limit=MAX_NOTES)
    notes.sort(key=lambda n: n.created_at, reverse=True)
    events = await repository.recent_events(session, user_id, limit=MAX_EVENTS)
    debriefs = await repository.recent_debrief_summaries(session, user_id, limit=MAX_DEBRIEFS)

    return TutorMemoryRead(
        notes=[
            NoteRead(id=n.id, kind=n.kind, body=dict(n.body or {}), created_at=n.created_at)
            for n in notes[:MAX_NOTES]
        ],
        events=[
            EventRead(
                id=e.id,
                kind=e.kind,
                ref_kind=e.ref_kind,
                ref_id=e.ref_id,
                title=e.title,
                occurred_at=e.occurred_at,
            )
            for e in events
        ],
        debrief_summaries=[
            DebriefSummaryRead(
                id=d.id,
                attempt_id=d.attempt_id,
                key_insights=list(d.key_insights or []),
                action_plan=list(d.action_plan or []),
                narrative=d.narrative,
                created_at=d.created_at,
            )
            for d in debriefs
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

    Debrief summaries are opt-in rather than swept up with the rest: they are
    also the doctor's record of what a debrief concluded, shown on their own
    results, and somebody clearing the tutor's memory is usually not asking to
    delete those as well.
    """
    counts = await repository.delete_all_for_user(session, user_id, include_debriefs=include_debriefs)
    return ForgottenCounts(**counts)


async def _exam_id(session: AsyncSession, exam_code: str | None) -> uuid.UUID | None:
    """Resolve an exam code, or record the event without one.

    A code the catalogue does not have is not worth failing over: the event is
    still a true thing the person did, and the exam only narrows the brief.
    """
    if not exam_code:
        return None
    for ref in await catalog.exam_refs(session):
        if ref.code == exam_code:
            return ref.id
    return None
