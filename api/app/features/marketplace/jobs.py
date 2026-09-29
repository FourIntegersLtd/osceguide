"""The worker task that queues the "starts in an hour" marketplace reminder."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.jobs import get_jobs_app
from app.core.logging import get_logger

log = get_logger(__name__)


def register() -> None:
    """Wire the reminder task into the shared jobs app, polling every five minutes."""
    app = get_jobs_app()

    @app.periodic(cron="*/5 * * * *")
    @app.task(name="send_marketplace_session_reminders", queue="marketplace")
    async def send_marketplace_session_reminders(timestamp: int = 0) -> None:
        """Run every five minutes: queue the reminder for every session that has
        entered its one-hour window and not already been claimed."""
        from app.core.db import job_session
        from app.features.marketplace.service_reminders import send_due_reminders

        async with job_session() as session:
            claimed = await send_due_reminders(session, now=datetime.now(UTC))
            if claimed:
                log.info("marketplace session reminders queued", sessions=claimed)
