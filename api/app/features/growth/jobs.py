"""Growth's background work: flagging a partner pilot's spend as it crosses a threshold."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.jobs import get_jobs_app
from app.core.logging import get_logger

log = get_logger(__name__)


def register() -> None:
    """Wire up growth's background jobs on the shared jobs app."""
    app = get_jobs_app()

    @app.periodic(cron="15 6 * * *")
    @app.task(name="check_partner_spend", queue="growth")
    async def check_partner_spend(timestamp: int = 0) -> None:
        """Queue an alert for any pilot partner whose estimated spend crossed a threshold.

        Daily: spend accrues by clicks, and the thresholds are hundreds of
        pounds apart, so a day's lag is well inside what the alert is for.
        """
        from app.core.db import job_session
        from app.features.growth.service_spend import check_spend_alerts

        async with job_session() as session:
            alerted = await check_spend_alerts(session, now=datetime.now(UTC))
            if alerted:
                log.info("partner spend alerts queued", partners=alerted)
