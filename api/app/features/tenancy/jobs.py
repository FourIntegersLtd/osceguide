"""Enforcing what the console only records."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.jobs import get_jobs_app
from app.core.logging import get_logger

log = get_logger(__name__)


def register() -> None:
    app = get_jobs_app()

    @app.periodic(cron="0 * * * *")
    @app.task(name="suspend_lapsed_organizations", queue="tenancy")
    async def suspend_lapsed_organizations(timestamp: int = 0) -> None:
        """Suspend organisations whose contract end date has passed.

        Hourly, because a contract ends on a day, not a second, and the
        suspension is reversible with the routes the console already has.
        """
        from app.core.db import job_session
        from app.features.tenancy.service_platform import suspend_lapsed_organizations as run

        async with job_session() as session:
            slugs = await run(session, now=datetime.now(UTC))
            if slugs:
                log.info("organisations suspended for lapsed contracts", slugs=slugs)
