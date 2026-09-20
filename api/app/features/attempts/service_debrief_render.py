"""Render the tutor from the source consultation, never the patient's prompt."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import RenderFailed
from app.features.attempts import errors, repository, repository_transcript
from app.features.attempts.models import Attempt


async def render_debrief(
    session: AsyncSession, attempt: Attempt, *, examiner_context: str | None
) -> dict[str, Any]:
    source = (
        await repository.attempt_by_id(session, attempt.source_attempt_id)
        if attempt.source_attempt_id else None
    )
    if source is None or source.user_id != attempt.user_id:
        raise errors.AttemptNotReady("The source consultation is unavailable.")
    messages = await repository_transcript.chunks_for(session, source.id)
    if not messages:
        raise errors.AttemptNotReady("A debrief needs a recorded consultation.")
    results = await repository_transcript.results_for(session, source.id)
    frozen_context = ((source.definition or {}).get("scenario") or {}).get("examiner_context")
    try:
        from osce_assessment.prompts.debrief_prompt import DebriefPromptFormatter
        from osce_assessment.prompts.debrief_transcript import TranscriptFormatter
        from osce_assessment.prompts.greetings import DEBRIEF_GREETING
    except ImportError as exc:
        raise RenderFailed("The assessment engine's debrief renderer is unavailable.") from exc
    transcript = TranscriptFormatter.format({
        "transcript_message": [{"role": row.role, "message": row.message} for row in messages],
    })
    return {
        "instructions": DebriefPromptFormatter.create_prompt(
            transcript=transcript,
            management_plan=frozen_context or examiner_context,
            sca_feedback=json.dumps([row.payload for row in results], ensure_ascii=False) if results else None,
        ),
        "greeting": DEBRIEF_GREETING,
        "examiner_context": frozen_context or examiner_context,
    }
