"""The worker task that erases accounts closed more than 30 days ago (E-4)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.jobs import get_jobs_app
from app.core.logging import get_logger

log = get_logger(__name__)


def register() -> None:
    """Wire the erasure task into the shared jobs app, on its own daily schedule."""
    app = get_jobs_app()

    @app.periodic(cron="0 3 * * *")
    @app.task(name="erase_closed_accounts", queue="identity")
    async def erase_closed_accounts(timestamp: int = 0) -> None:
        """Run once a day: scrub every account closed 30+ days ago that has
        not already been erased."""
        from app.core.db import job_session
        from app.features.identity.service_erasure import erase_due_accounts

        async with job_session() as session:
            erased = await erase_due_accounts(session, now=datetime.now(UTC))
            if erased:
                log.info("accounts erased", count=erased)
