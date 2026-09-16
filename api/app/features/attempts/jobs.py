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
from app.features.attempts import domain, repository
from app.features.attempts import repository_transcript as transcripts

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
        # Nothing to mark yet, or the attempt failed. Not an error: a job can
        # arrive before the status settles, or after a later failure.
        return False

    turns = await transcripts.chunks_for(session, attempt_id)
    if not turns:
        await repository.set_status(session, attempt_id, status="failed", at=now, reason="empty_transcript")
        return False

    try:
        payload = await evaluator.evaluate(
            framework_id=framework_id,
            policy_version=policy_version,
            transcript=[{"role": t.role, "message": t.message, "seq": t.seq} for t in turns],
        )
    except EvaluationFailed as exc:
        # The attempt is left at interaction_complete so a retry can mark it;
        # failing the attempt here would discard a transcript we still hold.
        log.warning("evaluation failed", attempt_id=str(attempt_id), error=str(exc))
        raise

    await transcripts.save_result(
        session,
        attempt_id,
        framework_id=framework_id,
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

        async with job_session() as session:
            await score_attempt_now(
                session,
                uuid.UUID(attempt_id),
                evaluator=build_evaluator(),
                policy_version=policy_version,
                framework_id=framework_id,
                now=datetime.now(UTC),
            )
