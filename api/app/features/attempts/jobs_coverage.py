"""Coalesce incoming turns while serialising coverage work per attempt."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import defer_in_transaction, get_jobs_app
from app.features.attempts.models import Attempt
from app.features.attempts.service_coverage import framework_for

TASK = "update_attempt_coverage"


async def enqueue_coverage(session: AsyncSession, attempt: Attempt) -> None:
    """Nudge coverage for the transcript as it stands, coalescing on purpose.

    A turn that lands while a coverage job is still waiting asks for nothing the
    waiting job will not do itself: it recomputes from the committed transcript
    when it starts. The queueing lock covers `todo` rows only, so a turn arriving
    while a job is *running* still queues a follow-up and no seq is lost.

    Letting the duplicate raise would not merely fail the worker's POST for a
    provisional panel: `complete_interaction` defers the marking in the same
    transaction, and a lock trip aborts that too, so an attempt would finish with
    no marking queued.
    """
    if framework_for(attempt) is None:
        return
    await defer_in_transaction(
        session,
        queue="coverage",
        task=TASK,
        args={"attempt_id": str(attempt.id)},
        queueing_lock=f"coverage:{attempt.id}",
        lock=f"coverage:{attempt.id}",
        ignore_lock_conflict=True,
    )


def register() -> None:
    @get_jobs_app().task(name=TASK, queue="coverage")
    async def update_attempt_coverage(attempt_id: str) -> None:
        from app.core.db import job_session
        from app.features.attempts.service_coverage import update_coverage

        async with job_session() as session:
            await update_coverage(session, uuid.UUID(attempt_id))
