"""The background job that reads a CV's text into sections.

Enqueued in the same transaction as the row it concerns (ADR 0006): either the
`processing` row and its job both land or neither does, so a row is never left
waiting for a job that rolled back. The model call runs here rather than in the
request, so a slow model is a slow job and not a slow upload.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import defer_in_transaction, get_jobs_app
from app.core.logging import get_logger
from app.core.settings import get_settings

log = get_logger(__name__)

QUEUE = "cv"
TASK = "extract_cv"


async def enqueue_extraction(session: AsyncSession, *, cv_id: uuid.UUID) -> None:
    """Queue the read for one CV. The queueing lock makes a redelivery idempotent."""
    await defer_in_transaction(
        session, queue=QUEUE, task=TASK, args={"cv_id": str(cv_id)}, queueing_lock=f"cv:{cv_id}"
    )


def register() -> None:
    app = get_jobs_app()

    @app.task(name=TASK, queue=QUEUE)
    async def extract_cv(cv_id: str) -> None:
        from app.core.db import job_session
        from app.features.cv.service import run_extraction_job

        async with job_session() as session:
            await run_extraction_job(
                session, uuid.UUID(cv_id), settings=get_settings(), now=datetime.now(UTC)
            )
            log.info("cv read", cv_id=cv_id)
