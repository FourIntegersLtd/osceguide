"""Scoring a delivered transcript.

Enqueued inside the transaction that marks the transcript complete, so the work
and the fact that it is owed are recorded together: either both land or
neither. b2c ran this on a thread pool and b2b on a raw daemon thread, so a
deploy mid-generation stranded `feedback_status='generating'` forever.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import get_jobs_app
from app.core.logging import get_logger
from app.core.ports import EvaluationFailed, Evaluator
from app.features.attempts import domain, published_marking, repository
from app.features.attempts import repository_transcript as transcripts
from app.features.catalog import repository as catalog_repository

log = get_logger(__name__)

PLATFORM_DEFAULT_POLICY = "platform-default@1"

# An attempt can be marked once its interaction finished, and marked again
# afterwards under a different policy — a new org rubric, or a model change we
# want to compare against what a candidate was actually told. The second run
# adds a result; it does not move the attempt's status anywhere.
MARKABLE = frozenset({domain.Status.INTERACTION_COMPLETE, domain.Status.EVALUATED})


async def score_attempt_now(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    evaluator: Evaluator,
    policy_version: str,
    framework_id: str,
    now: datetime,
) -> bool:
    """Score once per policy version. Returns whether anything was written.

    Idempotent by design: the queue may deliver a job more than once, and a
    retry after a partial failure must not produce a second result for the same
    policy. Re-scoring under a *different* policy is a new row beside the old.
    """
    scored = await transcripts.scored_policy_versions(session, attempt_id)
    if not domain.should_score(scored_versions=scored, policy_version=policy_version):
        return False

    attempt = await repository.attempt_by_id(session, attempt_id)
    if attempt is None:
        log.warning("scoring skipped, attempt gone", attempt_id=str(attempt_id))
        return False
    status = domain.Status(attempt.status)
    if status not in MARKABLE:
        return False

    exam_code = await catalog_repository.exam_code_by_id(session, attempt.exam_id)
    rubric = published_marking.rubric_for_scoring(
        attempt.definition if isinstance(attempt.definition, dict) else None,
        exam_code=exam_code,
    )
    if rubric is None:
        log.warning("scoring skipped, no rubric for attempt", attempt_id=str(attempt_id))
        return False

    turns = await transcripts.chunks_for(session, attempt_id)
    if not turns:
        await repository.set_status(session, attempt_id, status="failed", at=now, reason="empty_transcript")
        return False

    resolved_framework_id = str(
        (rubric.get("framework") or {}).get("id")
        if isinstance(rubric.get("framework"), dict)
        else framework_id
    )

    try:
        payload = await evaluator.evaluate(
            rubric=rubric,
            policy_version=policy_version,
            transcript=[{"role": t.role, "message": t.message, "seq": t.seq} for t in turns],
        )
    except EvaluationFailed as exc:
        log.warning("evaluation failed", attempt_id=str(attempt_id), error=str(exc))
        raise

    await transcripts.save_result(
        session,
        attempt_id,
        framework_id=resolved_framework_id or framework_id,
        policy_version=policy_version,
        payload=payload,
        model_used=str(payload.get("model_used") or "") or None,
        at=now,
    )
    if status is domain.Status.INTERACTION_COMPLETE:
        await repository.set_status(session, attempt_id, status="evaluated", at=now)
    return True


def register() -> None:
    """Declare the task with procrastinate.

    Kept behind a function so importing this module for its logic — which the
    tests do — does not require a configured queue.
    """
    app = get_jobs_app()

    @app.task(name="score_attempt", queue="scoring")
    async def score_attempt(attempt_id: str, policy_version: str, framework_id: str) -> None:
        from datetime import UTC

        from app.core.db import job_session
        from app.features.attempts.evaluator import build_evaluator

        at = datetime.now(UTC)
        attempt_uuid = uuid.UUID(attempt_id)

        async with job_session() as session:
            try:
                evaluator = build_evaluator()
            except EvaluationFailed as exc:
                await repository.set_status(
                    session,
                    attempt_uuid,
                    status="failed",
                    at=at,
                    reason=str(exc)[:500],
                )
                log.error("scoring aborted, engine unavailable", attempt_id=attempt_id, error=str(exc))
                return

            try:
                await score_attempt_now(
                    session,
                    attempt_uuid,
                    evaluator=evaluator,
                    policy_version=policy_version,
                    framework_id=framework_id,
                    now=at,
                )
            except EvaluationFailed as exc:
                await repository.set_status(
                    session,
                    attempt_uuid,
                    status="failed",
                    at=at,
                    reason=str(exc)[:500],
                )
                log.error("scoring failed", attempt_id=attempt_id, error=str(exc))
