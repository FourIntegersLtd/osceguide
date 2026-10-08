"""The queue looking after itself."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.jobs import get_jobs_app


def register() -> None:
    """Wire up health's background jobs on the shared jobs app."""
    app = get_jobs_app()

    @app.periodic(cron="*/5 * * * *")
    @app.task(name="reclaim_stalled_jobs", queue="health")
    async def reclaim_stalled_jobs(timestamp: int = 0) -> None:
        """Requeue or fail the jobs a dead worker left `doing`, and fail consumer attempts
        abandoned for over three hours, every five minutes."""
        from app.core.db import job_session
        from app.features.health.service import run_sweep

        await run_sweep(job_session, now=datetime.now(UTC))
