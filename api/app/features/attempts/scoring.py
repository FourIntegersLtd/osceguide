"""Deciding how an attempt will be marked, and queueing the work.

Which policy applies is a backend decision made after the interaction is over.
The worker is never told any of it.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.features.attempts import repository
from app.features.attempts.models import Attempt

log = get_logger(__name__)

PLATFORM_DEFAULT_POLICY = "platform-default@1"
SCORING_QUEUE = "scoring"
SCORING_TASK = "score_attempt"


def policy_for(attempt: Attempt) -> tuple[str, str]:
    """The (framework_id, policy_version) an attempt will be marked under.

    Taken from the frozen definition, so re-marking a past attempt uses the
    framework it was actually run against rather than whatever the station says
    today. An org feedback template will narrow this later; the default is the
    platform's own rubric.
    """
    definition = attempt.definition or {}
    framework_id = str(definition.get("framework_id") or "")
    policy = definition.get("evaluation_policy") or {}
    version = str(policy.get("version") or PLATFORM_DEFAULT_POLICY)
    return framework_id, version


async def enqueue_scoring(session: AsyncSession, attempt: Attempt, *, now: datetime) -> None:
    """Queue the marking in the caller's transaction.

    Deliberately not `app.defer_async`: procrastinate's own connector holds its
    own pool, so deferring through it commits the job on a different connection
    and the "enqueue with the data" guarantee in ADR 0006 quietly does not hold
    — the job could land while the transcript that justified it rolls back.

    Calling procrastinate's own SQL function on our session keeps one
    transaction, at the cost of naming the queue and task here rather than
    through the task object. The queueing lock makes it idempotent: a redelivered
    transcript cannot queue a second marking of the same attempt.
    """
    framework_id, policy_version = policy_for(attempt)
    if not framework_id:
        # Nothing frozen means nothing to mark against. The transcript is kept;
        # this is visible in the logs rather than silently dropped.
        log.warning("scoring not queued, no framework on the attempt", attempt_id=str(attempt.id))
        return

    await repository.defer_job(
        session,
        queue=SCORING_QUEUE,
        task=SCORING_TASK,
        queueing_lock=f"score:{attempt.id}:{policy_version}",
        args={
            "attempt_id": str(attempt.id),
            "policy_version": policy_version,
            "framework_id": framework_id,
        },
    )
