"""Coalesce incoming turns while serialising coverage work per attempt."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import defer_in_transaction, get_jobs_app
from app.features.attempts.models import Attempt
from app.features.attempts.service_coverage import framework_for

TASK = "update_attempt_coverage"


async def enqueue_coverage(session: AsyncSession, attempt: Attempt) -> None:
    if framework_for(attempt) is None:
        return
    await defer_in_transaction(
        session,
        queue="coverage",
        task=TASK,
        args={"attempt_id": str(attempt.id)},
        queueing_lock=f"coverage:{attempt.id}",
        lock=f"coverage:{attempt.id}",
    )


def register() -> None:
    @get_jobs_app().task(name=TASK, queue="coverage")
    async def update_attempt_coverage(attempt_id: str) -> None:
        from app.core.db import job_session
        from app.features.attempts.service_coverage import update_coverage

        async with job_session() as session:
            await update_coverage(session, uuid.UUID(attempt_id))
