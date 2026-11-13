"""Writing the non-verbal section once a consultation is over, in the background."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

import procrastinate
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionOpener
from app.core.jobs import defer_in_transaction, get_jobs_app
from app.core.logging import get_logger
from app.core.ports import TranscriptSummariser
from app.features.attempts import repository_nonverbal as store
from app.features.attempts.jobs import is_last_try
from app.features.attempts.models import Attempt

log = get_logger(__name__)

TASK = "summarise_attempt_nonverbal"
# Shares the coverage queue (and its worker) on purpose: both are light, post-consultation model calls
# on the same schedule, and a new queue would need its own worker entry and deploy config.
QUEUE = "coverage"

# A model call fails for reasons that pass. A job runs 1 + 2 times, 4 s then 16 s apart; the last try
# stores `failed` instead of raising, because a raise rolls the job's writes back.
RETRY = procrastinate.RetryStrategy(max_attempts=3, exponential_wait=4)


async def on_interaction_complete(session: AsyncSession, attempt: Attempt) -> None:
    """Queue the written section in the transaction that finishes the consultation, if video came in.

    Coalesced like coverage: a duplicate must not raise, since `complete_interaction` defers the
    marking in the same transaction and a lock trip would abort that too.
    """
    if not await store.has_batches(session, attempt.id):
        return
    await defer_in_transaction(
        session,
        queue=QUEUE,
        task=TASK,
        args={"attempt_id": str(attempt.id)},
        queueing_lock=f"nonverbal:{attempt.id}",
        lock=f"nonverbal:{attempt.id}",
        ignore_lock_conflict=True,
    )


async def run(
    open_session: SessionOpener,
    attempt_id: uuid.UUID,
    *,
    build_summariser: Callable[[], TranscriptSummariser],
    now: datetime,
    last_try: bool,
) -> bool:
    """One run of the queued job. On the last try any error is recorded as `failed` and swallowed."""
    from app.features.attempts import service_nonverbal

    try:
        return await service_nonverbal.summarise(
            open_session, attempt_id, summariser=build_summariser(), now=now
        )
    except Exception:
        if not last_try:
            raise
        log.exception("non-verbal summary gave up", attempt_id=str(attempt_id))
        await service_nonverbal.record_failed(open_session, attempt_id, now=now)
        return False


def register() -> None:
    """Declare the task with procrastinate."""

    @get_jobs_app().task(name=TASK, queue=QUEUE, pass_context=True, retry=RETRY)
    async def summarise_attempt_nonverbal(context: procrastinate.JobContext, attempt_id: str) -> None:
        """The queued job: turn this attempt's per-second batches into the candidate's written section."""
        from app.core.db import job_session
        from app.features.tutor_memory.service import transcript_summariser

        await run(
            job_session,
            uuid.UUID(attempt_id),
            build_summariser=transcript_summariser,
            now=datetime.now(UTC),
            last_try=is_last_try(context.job, RETRY),
        )
