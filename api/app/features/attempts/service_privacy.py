"""What this slice hands the identity slice for a person's own data rights:
erasure (E-4) and export (E-5). Kept apart from `service.py`, which is about
running an attempt, not about what other slices may do with a finished one.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import repository, repository_nonverbal, repository_transcript


async def erase_content_for_user(session: AsyncSession, user_id: uuid.UUID) -> int:
    """Delete every transcript, delivery record and mark this person's
    attempts carry, keeping the attempt rows themselves. Returns how many
    attempts were touched, for the erasure job's own logging."""
    attempt_ids = await repository.attempt_ids_for_user(session, user_id)
    await repository_transcript.erase_content_for_attempts(session, attempt_ids)
    return len(attempt_ids)


async def export_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[dict[str, Any]]:
    """Every attempt this person has run, each carrying its own transcript and
    marks, shaped for the `/me/export` download."""
    attempts = await repository.all_for_user(session, user_id)
    exported: list[dict[str, Any]] = []
    for attempt in attempts:
        messages = await repository_transcript.chunks_for(session, attempt.id)
        transcript = await repository_transcript.transcript_for(session, attempt.id)
        results = await repository_transcript.results_for(session, attempt.id)
        nonverbal = await repository_nonverbal.summary_for(session, attempt.id)
        exported.append(
            {
                "id": attempt.id,
                "kind": attempt.kind,
                "status": attempt.status,
                "started_at": attempt.started_at,
                "completed_at": attempt.completed_at,
                "transcript": {
                    "complete": transcript.complete if transcript else False,
                    "messages": [
                        {"role": message.role, "message": message.message, "spoken_at": message.spoken_at}
                        for message in messages
                    ],
                },
                "nonverbal": {"facts": nonverbal.facts, "feedback": nonverbal.feedback}
                if nonverbal
                else None,
                "results": [
                    {
                        "framework_id": result.framework_id,
                        "policy_version": result.policy_version,
                        "payload": result.payload,
                        "scored_at": result.scored_at,
                    }
                    for result in results
                ],
            }
        )
    return exported


async def export_nonverbal_consent_for_user(
    session: AsyncSession, user_id: uuid.UUID
) -> dict[str, Any] | None:
    """The person's answer to the camera-feedback invitation, or None if they never answered."""
    consent = await repository_nonverbal.consent_for(session, user_id)
    if consent is None:
        return None
    return {
        "version": consent.version,
        "consented_at": consent.consented_at,
        "withdrawn_at": consent.withdrawn_at,
    }
