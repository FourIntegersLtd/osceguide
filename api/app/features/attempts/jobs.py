"""Marking a delivered transcript: deciding how, queueing it, and running it.

Which policy applies is a backend decision made after the interaction is over; the worker is never
told any of it. The job is enqueued inside the transaction that marks the transcript complete, so the
work and the fact that it is owed are recorded together: either both land or neither.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import procrastinate
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionOpener
from app.core.events import publish_after_commit, user_topic
from app.core.jobs import defer_in_transaction, get_jobs_app
from app.core.logging import get_logger
from app.core.ports import EvaluationFailed, Evaluator
from app.features.attempts import domain, domain_definition, repository
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.models import Attempt
from app.features.sittings import service_reads as sittings_reads

log = get_logger(__name__)

PLATFORM_DEFAULT_POLICY = "platform-default@1"
SCORING_QUEUE = "scoring"
SCORING_TASK = "score_attempt"
COMPACTION_BATCH = 50

# A model call fails for reasons that pass: a timeout, a rate limit, a malformed answer. procrastinate
# retries while `job.attempts` (the failed runs so far) is under `max_attempts`, so a job runs 1 + 4
# times, 4 s, 16 s, 64 s then 256 s apart. The run it will not retry is the last try: whatever goes wrong
# there is recorded on the attempt (`scoring_failed`) instead of raised, because a raise rolls the
# job's writes back.
SCORING_RETRY = procrastinate.RetryStrategy(max_attempts=4, exponential_wait=4)

# An attempt can be marked once its interaction finished, and marked again
# afterwards under a different policy — a new org rubric, or a model change we
# want to compare against what a candidate was actually told. The second run
# adds a result; it does not move the attempt's status anywhere.
MARKABLE = frozenset({domain.Status.INTERACTION_COMPLETE, domain.Status.EVALUATED})


def is_last_try(job: procrastinate.jobs.Job, retry: procrastinate.RetryStrategy = SCORING_RETRY) -> bool:
    """Whether the queue will not run this job again if it fails now under `retry`."""
    return retry.get_retry_decision(exception=Exception(), job=job) is None


def can_mark(attempt: Attempt) -> bool:
    """Whether a rubric is frozen on the attempt. A legacy migrated attempt has none."""
    framework_id, _ = policy_for(attempt)
    return bool(framework_id) and domain_definition.rubric_for(attempt.definition) is not None


async def record_marking_gave_up(session: AsyncSession, attempt_id: uuid.UUID) -> None:
    """Say on a finished attempt that the scorer gave up, and tell whoever is waiting on it.

    Only an attempt still awaiting its first mark is touched: one already marked has its result.
    """
    attempt = await repository.attempt_by_id(session, attempt_id)
    if attempt is None or attempt.status != domain.Status.INTERACTION_COMPLETE:
        return
    await repository.set_scoring_failure(session, attempt_id, reason=domain.SCORING_FAILED)
    publish_after_commit(session, user_topic(attempt.user_id), "attempt", {"attempt_id": str(attempt_id)})
    await sittings_reads.attempt_progress(session, attempt)


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
    if not can_mark(attempt):
        # No frozen definition, so the worker never bootstrapped this attempt —
        # yet a transcript arrived for it. There is nothing to mark it against:
        # the rubric is the wording somebody was assessed under, and it cannot
        # be reconstructed after the fact from an id. Only this first enqueue, right after the
        # interaction, may fail the attempt; a rescore refuses instead (see `can_mark`).
        log.warning(
            "not queueing a marking for an attempt with no frozen rubric",
            attempt_id=str(attempt.id),
            reason="attempt_not_rendered",
        )
        if domain.Status(attempt.status) not in (domain.Status.EVALUATED, domain.Status.FAILED):
            # Said on the attempt, not only in a log: staff and the candidate are waiting on it.
            await repository.set_status(
                session, attempt.id, status=domain.Status.FAILED, at=now, reason=domain.NO_MARKING_RUBRIC
            )
            publish_after_commit(
                session, user_topic(attempt.user_id), "attempt", {"attempt_id": str(attempt.id)}
            )
            await sittings_reads.attempt_progress(session, attempt)
        return

    await defer_in_transaction(
        session,
        queue=SCORING_QUEUE,
        task=SCORING_TASK,
        queueing_lock=f"score:{attempt.id}:{policy_version}",
        # One attempt is marked by one run at a time, whatever the policies; marking goes before chores.
        lock=f"score:{attempt.id}",
        priority=10,
        args={
            "attempt_id": str(attempt.id),
            "policy_version": policy_version,
            "framework_id": framework_id,
        },
    )


@dataclass(frozen=True)
class PreparedScoring:
    """What the model call needs, read in a short session that is closed before the call.

    Plain values, not ORM rows: they outlive the session that loaded them.
    """

    attempt_id: uuid.UUID
    rubric: dict[str, Any]
    transcript: list[dict[str, Any]]
    policy_version: str
    framework_id: str


async def prepare_scoring(
    session: AsyncSession, attempt_id: uuid.UUID, *, policy_version: str, framework_id: str, now: datetime
) -> PreparedScoring | None:
    """Decide whether to mark, and gather what marking needs. `None` means nothing to mark.

    Also the home of the two outcomes that need no model: a mark already there (clear any stale
    failure) and an empty transcript (fail the attempt, loudly).
    """
    attempt = await repository.attempt_by_id(session, attempt_id)
    if attempt is None:
        log.warning("scoring skipped, attempt gone", attempt_id=str(attempt_id))
        return None
    scored = await transcripts.scored_policy_versions(session, attempt_id)
    if not domain.should_score(scored_versions=scored, policy_version=policy_version):
        # A mark landed some other way (a re-run, a manual one) while a failure was still recorded.
        await _clear_scoring_failure(session, attempt)
        return None
    status = domain.Status(attempt.status)
    if status not in MARKABLE:
        # Nothing to mark yet, or the attempt failed. Not an error: a job can
        # arrive before the status settles, or after a later failure.
        return None

    # The rubric travels on the attempt rather than in the job's arguments: it
    # is the whole framework, its prompt and its clock, and reading it back
    # from the frozen definition is what makes a re-mark reproduce the original.
    rubric = domain_definition.rubric_for(attempt.definition)
    if rubric is None:
        log.warning("scoring skipped, attempt has no frozen rubric", attempt_id=str(attempt_id))
        return None

    turns = await transcripts.chunks_for(session, attempt_id)
    if not turns:
        await repository.set_status(
            session, attempt_id, status=domain.Status.FAILED, at=now, reason="empty_transcript"
        )
        # Announced as loudly as a success: somebody is watching this attempt
        # waiting for feedback, and a failure they are never told about is a
        # spinner that turns for ever.
        publish_after_commit(session, user_topic(attempt.user_id), "attempt", {"attempt_id": str(attempt_id)})
        await sittings_reads.attempt_progress(session, attempt)
        return None

    return PreparedScoring(
        attempt_id=attempt_id,
        rubric=rubric,
        transcript=[{"role": turn.role, "message": turn.message, "seq": turn.seq} for turn in turns],
        policy_version=policy_version,
        framework_id=framework_id,
    )


async def record_scoring(
    session: AsyncSession, prepared: PreparedScoring, marks: dict[str, Any], *, now: datetime
) -> bool:
    """Store the marks. Returns whether anything was written.

    The model took a minute or two with no transaction open, so the attempt may have moved: another
    run may have marked this policy, or the attempt may have failed. Both are checked again here.
    """
    attempt_id = prepared.attempt_id
    attempt = await repository.attempt_by_id(session, attempt_id)
    if attempt is None:
        return False
    scored = await transcripts.scored_policy_versions(session, attempt_id)
    if not domain.should_score(scored_versions=scored, policy_version=prepared.policy_version):
        await _clear_scoring_failure(session, attempt)
        return False
    status = domain.Status(attempt.status)
    if status not in MARKABLE:
        return False

    # The model is the row's own column, not a mark: left in the payload it is
    # a top-level key the rubric's derived schema forbids, so no stored result
    # validated against the schema it was marked with.
    marks = dict(marks)
    model_used = str(marks.pop("model_used", "") or "") or None
    # Typed loosely on purpose: it returns a row today and a bool once saving is insert-or-skip.
    saved: object = await transcripts.save_result(
        session,
        attempt_id,
        framework_id=str(prepared.rubric.get("framework", {}).get("id") or prepared.framework_id),
        policy_version=prepared.policy_version,
        payload=marks,
        model_used=model_used,
        at=now,
    )
    if saved is False:
        # Lost the race to another run that stored the same policy's mark; it did the rest.
        return False
    if status is domain.Status.INTERACTION_COMPLETE:
        await repository.set_status(session, attempt_id, status=domain.Status.EVALUATED, at=now)
    await _clear_scoring_failure(session, attempt)
    # Marking takes a minute or two of model time, so the browser has to learn
    # it finished somehow. b2c polled; this says so once, after the commit,
    # and the poll goes.
    publish_after_commit(session, user_topic(attempt.user_id), "attempt", {"attempt_id": str(attempt_id)})
    await sittings_reads.attempt_progress(session, attempt)
    return True


async def score_attempt_now(
    open_session: SessionOpener,
    attempt_id: uuid.UUID,
    *,
    evaluator: Evaluator,
    policy_version: str,
    framework_id: str,
    now: datetime,
) -> bool:
    """Score once per policy version. Returns whether anything was written.

    Three steps, so no database connection is held while the model thinks: read in a short session,
    call the model with none open, then write in another. A failed evaluation raises, and the queue
    retries; `score_attempt_job` records the last failure.

    Idempotent by design: the queue may deliver a job more than once, and a
    retry after a partial failure must not produce a second result for the same
    policy. Re-scoring under a *different* policy is a new row beside the old.
    """
    async with open_session() as session:
        prepared = await prepare_scoring(
            session, attempt_id, policy_version=policy_version, framework_id=framework_id, now=now
        )
    if prepared is None:
        return False
    try:
        marks = await evaluator.evaluate(
            rubric=prepared.rubric, policy_version=policy_version, transcript=prepared.transcript
        )
    except EvaluationFailed as exc:
        # The attempt stays at interaction_complete so a retry can mark it;
        # failing it would discard a transcript we still hold.
        log.warning("evaluation failed", attempt_id=str(attempt_id), error=str(exc))
        raise
    async with open_session() as session:
        return await record_scoring(session, prepared, marks, now=now)


async def _clear_scoring_failure(session: AsyncSession, attempt: Attempt) -> None:
    """Take "marking failed" off an attempt once a mark exists, so staff and candidate stop seeing it."""
    if attempt.failed_reason == domain.SCORING_FAILED:
        await repository.set_scoring_failure(session, attempt.id, reason=None)


async def score_attempt_job(
    attempt_id: uuid.UUID,
    *,
    build_evaluator: Callable[[], Evaluator],
    policy_version: str,
    framework_id: str,
    now: datetime,
    last_try: bool,
    open_session: SessionOpener,
) -> bool:
    """One run of the queued job. On the last try any error is recorded on the attempt and swallowed.

    Not just `EvaluationFailed`: building the evaluator, a database error and an integrity error all
    end with a candidate waiting on a spinner unless the attempt says marking gave up. The failed run's
    session rolls back, so the record is written in a session of its own.
    """
    try:
        return await score_attempt_now(
            open_session,
            attempt_id,
            evaluator=build_evaluator(),
            policy_version=policy_version,
            framework_id=framework_id,
            now=now,
        )
    except Exception:
        if not last_try:
            raise
        log.exception("marking gave up", attempt_id=str(attempt_id))
        async with open_session() as session:
            await record_marking_gave_up(session, attempt_id)
        return False


def register() -> None:
    """Declare the task with procrastinate.

    Kept behind a function so importing this module for its logic — which the
    tests do — does not require a configured queue.
    """
    from app.features.attempts.jobs_coverage import register as register_coverage
    from app.features.attempts.jobs_nonverbal import register as register_nonverbal

    register_coverage()
    register_nonverbal()
    app = get_jobs_app()

    @app.task(
        name=SCORING_TASK,
        queue=SCORING_QUEUE,
        pass_context=True,
        retry=SCORING_RETRY,
    )
    async def score_attempt(
        context: procrastinate.JobContext, attempt_id: str, policy_version: str, framework_id: str
    ) -> None:
        """The queued job: build a fresh evaluator and score this attempt now."""
        from datetime import UTC

        from app.core.db import job_session
        from app.features.attempts.evaluator import build_evaluator

        await score_attempt_job(
            uuid.UUID(attempt_id),
            build_evaluator=build_evaluator,
            policy_version=policy_version,
            framework_id=framework_id,
            now=datetime.now(UTC),
            last_try=is_last_try(context.job),
            open_session=job_session,
        )

    @app.periodic(cron="*/10 * * * *")
    @app.task(name="compact_transcripts", queue="attempts")
    async def compact_transcripts(timestamp: int = 0) -> None:
        """Fold finished transcripts' rows into one document each, every ten minutes. Then remove the
        transcripts that have outlived their organisation's retention."""
        from app.core.db import job_session
        from app.features.attempts.service_compaction import compact_ready_transcripts
        from app.features.attempts.service_retention import sweep_retention

        await compact_ready_transcripts(job_session, limit=COMPACTION_BATCH)
        # Same schedule: the sweep is a cheap indexed read when nothing has expired.
        await sweep_retention(job_session, now=datetime.now(UTC))
        # And the raw non-verbal batches no summary job will ever read (abandoned attempts, late batches).
        from app.features.attempts.service_nonverbal import sweep_orphan_batches

        await sweep_orphan_batches(job_session, now=datetime.now(UTC))
