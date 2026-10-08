"""The worker task that warns people their bought access is about to end."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.jobs import get_jobs_app
from app.core.logging import get_logger

log = get_logger(__name__)


def register() -> None:
    """Wire the expiry warning into the shared jobs app, hourly."""
    app = get_jobs_app()

    @app.periodic(cron="17 * * * *")
    @app.task(name="warn_expiring_access", queue="notifications")
    async def warn_expiring_access(timestamp: int = 0) -> None:
        """Queue the warning for every purchase now inside its last week."""
        from app.core.db import job_session
        from app.features.entitlements.service_expiry import warn_expiring_access as warn

        async with job_session() as session:
            queued = await warn(session, now=datetime.now(UTC))
            if queued:
                log.info("expiry warnings queued", count=queued)
