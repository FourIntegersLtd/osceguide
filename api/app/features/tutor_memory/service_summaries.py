"""Turning a finished conversation into something worth keeping.

Two conversations end with something the tutor needs next time: a dashboard
session, where a next step was agreed, and a debrief, where the doctor and the
tutor concluded something about a consultation. Both are summarised and the
turns behind the first are then deleted — what the tutor needs is what was
agreed, not a recording.

The prompts are ported from b2c's `DEBRIEF_SUMMARY_SYSTEM_PROMPT` with the
persona renamed: this backend has one tutor and does not name it in a prompt,
because the name is a product's and the engine is not.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.ports import SummaryFailed, TranscriptSummariser
from app.features.assistant import service_seams as assistant
from app.features.attempts import service_reads as attempts
from app.features.tutor_memory import domain, repository

log = get_logger(__name__)

SESSION_SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "agreed_next_steps": {"type": "array", "items": {"type": "string"}},
        "topics": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary"],
}

SESSION_SUMMARY_INSTRUCTIONS = """
You are reading back a conversation between a doctor and their tutor, and writing the note the
tutor will read before they next speak.

Write it as the tutor's own note, in the second person about the doctor ("they"), and include
nothing the transcript does not support.

- `summary`: two or three sentences on what was discussed and where it got to.
- `agreed_next_steps`: what the doctor said they would do, in their own terms. Empty if nothing
  was agreed; do not invent one.
- `topics`: a few short labels for what was covered.
""".strip()

DEBRIEF_SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "key_insights": {"type": "array", "items": {"type": "string"}},
        "action_plan": {"type": "array", "items": {"type": "string"}},
        "narrative_summary": {"type": "string"},
    },
    "required": ["key_insights", "action_plan", "narrative_summary"],
}

DEBRIEF_SUMMARY_INSTRUCTIONS = """
You are an expert medical educator reviewing a debrief between a doctor and their tutor.

Analyse the transcript and produce a structured summary. The tone must be collaborative, using
"we" to reflect what was concluded together.

- `key_insights`: the critical things noticed in the session.
- `action_plan`: actionable improvement steps. Each step must include a specific, quoted example
  of a phrase the doctor could use — for instance: 'To practise active listening, you could say:
  "So, if I am understanding correctly, you have been feeling..."'.
- `narrative_summary`: the debrief's primary themes, in a short paragraph.
""".strip()


async def summarise_assistant_session(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    summariser: TranscriptSummariser,
) -> bool:
    """Write the note, then delete the turns. Returns whether anything was written.

    Idempotent: a redelivered job finds the note already there and stops, which
    matters because the second half of this deletes the evidence.
    """
    if await repository.summary_for_session(session, session_id) is not None:
        return False
    ref = await assistant.session_ref(session, session_id)
    if ref is None:
        return False

    turns = await assistant.transcript_messages(session, session_id)
    if not turns:
        return False
    try:
        payload = await summariser.summarise(
            kind="session_summary",
            transcript=turns,
            schema=SESSION_SUMMARY_SCHEMA,
            instructions=SESSION_SUMMARY_INSTRUCTIONS,
        )
    except SummaryFailed as exc:
        # The turns are left in place so a retry can still summarise them.
        log.warning("session not summarised", session_id=str(session_id), error=str(exc))
        raise

    await repository.add_note(
        session,
        user_id=ref.user_id,
        exam_id=None,
        session_id=session_id,
        kind="session_summary",
        body={
            "summary": str(payload.get("summary") or ""),
            "agreed_next_steps": [
                {"text": step, "done": False}
                for step in domain.open_action_items([payload.get("agreed_next_steps") or []])
            ],
            "topics": [str(t) for t in _items(payload.get("topics"))],
        },
    )
    # Only once the note is written: the summary is what replaces the
    # recording, and deleting first would lose both if this failed.
    await assistant.discard_transcript(session, session_id)
    return True


async def summarise_debrief(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    summariser: TranscriptSummariser,
) -> bool:
    """Write what a debrief concluded. One per attempt, enforced by the table."""
    if await repository.debrief_summary_for_attempt(session, attempt_id) is not None:
        return False
    ref = await attempts.attempt_ref(session, attempt_id)
    if ref is None:
        return False

    transcript = await attempts.read_transcript(session, attempt_id, requester_id=ref.user_id, is_admin=False)
    if not domain.should_summarise_attempt(kind=ref.kind, complete=transcript.complete):
        return False
    if not transcript.messages:
        return False

    payload = await summariser.summarise(
        kind="debrief",
        transcript=[{"role": m.role, "message": m.message, "seq": m.seq} for m in transcript.messages],
        schema=DEBRIEF_SUMMARY_SCHEMA,
        instructions=DEBRIEF_SUMMARY_INSTRUCTIONS,
    )
    await repository.add_debrief_summary(
        session,
        attempt_id=attempt_id,
        user_id=ref.user_id,
        exam_id=ref.exam_id,
        key_insights=[str(i) for i in _items(payload.get("key_insights"))],
        action_plan=[{"text": str(step), "done": False} for step in _items(payload.get("action_plan"))],
        narrative=str(payload.get("narrative_summary") or "") or None,
        model_used=str(payload.get("model_used") or "") or None,
    )
    return True


def _items(value: Any) -> list[Any]:
    """A summariser's list field, however the model spelled it.

    Typed `object` because the port speaks plain dicts; a model that returned a
    string where a list was asked for is a bad summary, not a crash.
    """
    return list(value) if isinstance(value, list) else []
