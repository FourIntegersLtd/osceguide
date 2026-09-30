"""Marking a delivered transcript: deciding how, queueing it, and running it.

Which policy applies is a backend decision made after the interaction is over; the worker is never
told any of it. The job is enqueued inside the transaction that marks the transcript complete, so the
work and the fact that it is owed are recorded together: either both land or neither.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import publish_after_commit, user_topic
from app.core.jobs import defer_in_transaction, get_jobs_app
from app.core.logging import get_logger
from app.core.ports import EvaluationFailed, Evaluator
from app.features.attempts import domain, domain_definition, repository
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.models import Attempt

log = get_logger(__name__)

PLATFORM_DEFAULT_POLICY = "platform-default@1"
SCORING_QUEUE = "scoring"
SCORING_TASK = "score_attempt"

# An attempt can be marked once its interaction finished, and marked again
# afterwards under a different policy — a new org rubric, or a model change we
# want to compare against what a candidate was actually told. The second run
# adds a result; it does not move the attempt's status anywhere.
MARKABLE = frozenset({domain.Status.INTERACTION_COMPLETE, domain.Status.EVALUATED})


def policy_for(attempt: Attempt) -> tuple[str, str]:
    """The (framework_id, policy_version) an attempt will be marked under.

    Taken from the frozen definition, so re-marking a past attempt uses the
    rubric it was actually run against rather than whatever that rubric says
    today. Where a sitting's feedback template narrowed the marking, that is
    already baked into the frozen snapshot.
    """
    definition = attempt.definition or {}
    framework_id = str(definition.get("framework_id") or "")
    policy = definition.get("evaluation_policy") or {}
    version = str(policy.get("version") or PLATFORM_DEFAULT_POLICY)
    return framework_id, version


async def enqueue_scoring(
    session: AsyncSession, attempt: Attempt, *, now: datetime, policy_version: str | None = None
) -> None:
    """Queue the marking in the caller's transaction.

    Deliberately not `app.defer_async`: procrastinate's own connector holds its own pool, so deferring
    through it would commit the job on a different connection than the transcript write. See ADR 0006.
    The queueing lock makes it idempotent — a redelivered transcript cannot queue a second marking.
    """
    framework_id, frozen_version = policy_for(attempt)
    policy_version = policy_version or frozen_version
    if not framework_id or domain_definition.rubric_for(attempt.definition) is None:
        # No frozen definition, so the worker never bootstrapped this attempt —
        # yet a transcript arrived for it. There is nothing to mark it against:
        # the rubric is the wording somebody was assessed under, and it cannot
        # be reconstructed after the fact from an id.
        log.warning(
            "not queueing a marking for an attempt with no frozen rubric",
            attempt_id=str(attempt.id),
            reason="attempt_not_rendered",
        )
        return

    await defer_in_transaction(
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

    # The rubric travels on the attempt rather than in the job's arguments: it
    # is the whole framework, its prompt and its clock, and reading it back
    # from the frozen definition is what makes a re-mark reproduce the original.
    rubric = domain_definition.rubric_for(attempt.definition)
    if rubric is None:
        log.warning("scoring skipped, attempt has no frozen rubric", attempt_id=str(attempt_id))
        return False

    turns = await transcripts.chunks_for(session, attempt_id)
    if not turns:
        await repository.set_status(
            session, attempt_id, status=domain.Status.FAILED, at=now, reason="empty_transcript"
        )
        # Announced as loudly as a success: somebody is watching this attempt
        # waiting for feedback, and a failure they are never told about is a
        # spinner that turns for ever.
        publish_after_commit(session, user_topic(attempt.user_id), "attempt", {"attempt_id": str(attempt_id)})
        return False

    try:
        marks = await evaluator.evaluate(
            rubric=rubric,
            policy_version=policy_version,
            transcript=[{"role": turn.role, "message": turn.message, "seq": turn.seq} for turn in turns],
        )
    except EvaluationFailed as exc:
        # The attempt is left at interaction_complete so a retry can mark it;
        # failing the attempt here would discard a transcript we still hold.
        log.warning("evaluation failed", attempt_id=str(attempt_id), error=str(exc))
        raise

    # The model is the row's own column, not a mark: left in the payload it is
    # a top-level key the rubric's derived schema forbids, so no stored result
    # validated against the schema it was marked with.
    marks = dict(marks)
    model_used = str(marks.pop("model_used", "") or "") or None
    await transcripts.save_result(
        session,
        attempt_id,
        framework_id=str(rubric.get("framework", {}).get("id") or framework_id),
        policy_version=policy_version,
        payload=marks,
        model_used=model_used,
        at=now,
    )
    if status is domain.Status.INTERACTION_COMPLETE:
        await repository.set_status(session, attempt_id, status=domain.Status.EVALUATED, at=now)
    # Marking takes a minute or two of model time, so the browser has to learn
    # it finished somehow. b2c polled; this says so once, after the commit,
    # and the poll goes.
    publish_after_commit(session, user_topic(attempt.user_id), "attempt", {"attempt_id": str(attempt_id)})
    return True


def register() -> None:
    """Declare the task with procrastinate.

    Kept behind a function so importing this module for its logic — which the
    tests do — does not require a configured queue.
    """
    from app.features.attempts.jobs_coverage import register as register_coverage

    register_coverage()
    app = get_jobs_app()

    @app.task(name=SCORING_TASK, queue=SCORING_QUEUE)
    async def score_attempt(attempt_id: str, policy_version: str, framework_id: str) -> None:
        """The queued job: build a fresh evaluator and score this attempt now."""
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
