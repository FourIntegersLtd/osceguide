"""The worker task that drains the outbox."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.jobs import get_jobs_app
from app.core.logging import get_logger

log = get_logger(__name__)


def register() -> None:
    app = get_jobs_app()

    @app.periodic(cron="* * * * *")
    @app.task(name="deliver_outbound_messages", queue="notifications")
    async def deliver_outbound_messages(timestamp: int = 0) -> None:
        from app.core.db import job_session
        from app.features.notifications.sender import build_email_sender
        from app.features.notifications.service import deliver_due

        async with job_session() as session:
            sent, deferred = await deliver_due(session, sender=build_email_sender(), now=datetime.now(UTC))
            if sent or deferred:
                log.info("outbox drained", sent=sent, deferred=deferred)
