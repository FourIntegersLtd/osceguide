"""What support may do to an attempt, once `service_platform` has said what is wrong.

Three actions for three of the four causes of "no feedback". The fourth — the
worker never bootstrapped, so nothing was frozen — has no fix but a fresh
attempt, which is what `fail` makes room for.

Every one is idempotent or refused, and every one leaves an audit row: these
change what a candidate is told about their own consultation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.attempts import domain, errors, jobs, repository, service_platform, service_worker
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.models import Attempt
from app.features.attempts.schemas_platform import PlatformAttemptDetail, RescoreResult
from app.features.health import service_jobs
from app.features.tenancy import service_audit


async def _require(session: AsyncSession, attempt_id: uuid.UUID) -> Attempt:
    """Fetch the attempt these actions act on, or refuse if it does not exist."""
    attempt = await repository.attempt_by_id(session, attempt_id)
    if attempt is None:
        raise errors.AttemptNotFound()
    return attempt


async def rescore(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    policy_version: str | None,
    actor: Principal,
    now: datetime,
) -> RescoreResult:
    """Queue the marking again.

    For a transcript that arrived and was never marked because the job failed or was never queued.
    The queueing lock makes a marking already waiting a no-op, and `score_attempt_now` makes a
    result already written one, so pressing this twice costs nothing. Naming a different policy
    version marks the same transcript again beside the old result, for comparison, not to hide it.
    """
    attempt = await _require(session, attempt_id)
    if domain.Status(attempt.status) not in jobs.MARKABLE:
        raise errors.InvalidAttemptState(f"An attempt that is {attempt.status} has nothing to mark.")
    _, frozen = jobs.policy_for(attempt)
    version = policy_version or frozen
    if version in await transcripts.scored_policy_versions(session, attempt_id):
        return RescoreResult(queued=False, policy_version=version, reason="already_scored")

    # Checked before deferring rather than left to the queueing lock: the
    # lock is a unique index, and tripping it inside the request's transaction
    # would abort the transaction rather than quietly decline.
    waiting = [
        job
        for job in await _scoring_jobs(session, attempt_id)
        if job.status == "todo" and job.args.get("policy_version") == version
    ]
    queued = not waiting
    if queued:
        await jobs.enqueue_scoring(session, attempt, now=now, policy_version=version)
    await service_audit.record(
        session,
        actor=actor,
        action="attempt.rescore_requested",
        target_type="attempt",
        target_id=str(attempt_id),
        summary=f"{version}: {'queued' if queued else 'already queued'}",
        meta={"user_id": str(attempt.user_id), "policy_version": version, "queued": queued},
    )
    return RescoreResult(queued=queued, policy_version=version, reason=None if queued else "already_queued")


async def salvage(
    session: AsyncSession, attempt_id: uuid.UUID, *, actor: Principal, now: datetime
) -> PlatformAttemptDetail:
    """Finish an interaction the worker never did.

    The turns arrived one by one and the final delivery never came — the
    worker died, or its last POST did. The chunks are the transcript; this
    marks them complete, moves the attempt on and queues the marking, exactly
    as the delivery would have. Refused with nothing to salvage: an attempt
    that never ran, or ran and has no turns, needs a fresh attempt instead.
    """
    attempt = await _require(session, attempt_id)
    if domain.Status(attempt.status) is not domain.Status.RUNNING:
        raise errors.InvalidAttemptState(
            f"Only a running attempt can be salvaged; this one is {attempt.status}."
        )
    turns = await transcripts.chunk_count(session, attempt_id)
    if turns == 0:
        raise errors.InvalidAttemptState("No turns were received, so there is no transcript to salvage.")
    await transcripts.mark_transcript_complete(session, attempt_id, runtime_label="salvaged", at=now)
    await service_worker.complete_interaction(session, attempt, now=now)
    await service_audit.record(
        session,
        actor=actor,
        action="attempt.salvaged",
        target_type="attempt",
        target_id=str(attempt_id),
        summary=f"{turns} turns marked complete and queued for marking",
        meta={"user_id": str(attempt.user_id), "chunk_count": turns},
    )
    return await service_platform.read_detail(session, attempt_id)


async def fail(
    session: AsyncSession, attempt_id: uuid.UUID, *, reason: str, actor: Principal, now: datetime
) -> PlatformAttemptDetail:
    """End an attempt that is going nowhere, so a fresh one can start.

    `failed` is terminal and nothing returns from it: the recording, such as it
    is, stays beside whatever the person does next. For an exam slot this
    frees the one-live-attempt index so a supervisor can re-dispatch; for a
    practice set it lets the person sit the station again.
    """
    attempt = await _require(session, attempt_id)
    from_status = attempt.status
    try:
        domain.transition(domain.Status(from_status), domain.Status.FAILED)
    except domain.InvalidTransition as exc:
        raise errors.InvalidAttemptState(str(exc)) from exc
    await repository.set_status(
        session, attempt_id, status=domain.Status.FAILED, at=now, reason=f"admin:{reason}"[:200]
    )
    await service_audit.record(
        session,
        actor=actor,
        action="attempt.failed_by_admin",
        target_type="attempt",
        target_id=str(attempt_id),
        summary=reason,
        meta={"user_id": str(attempt.user_id), "from_status": from_status, "reason": reason},
    )
    return await service_platform.read_detail(session, attempt_id)


async def _scoring_jobs(session: AsyncSession, attempt_id: uuid.UUID) -> list[service_jobs.JobRef]:
    """Every scoring job queued for this attempt, so `rescore` can tell a wait from a no-op."""
    return await service_jobs.jobs_for_arg(
        session, task_name=jobs.SCORING_TASK, key="attempt_id", values=[str(attempt_id)]
    )
