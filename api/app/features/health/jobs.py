"""The queue looking after itself."""

from __future__ import annotations

from datetime import UTC, datetime

from procrastinate import JobContext

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

    @app.periodic(cron="30 4 * * *")
    @app.task(name="record_database_size", queue="health")
    async def record_database_size(timestamp: int = 0) -> None:
        """Store the day's database size and raise the alarm at 60% and 80% of the budget, once a day."""
        from app.core.db import job_session
        from app.features.health.service import run_size_check

        await run_size_check(job_session, now=datetime.now(UTC))

    @app.periodic(cron="45 4 * * *")
    @app.task(name="prune_job_history", queue="health", pass_context=True)
    async def prune_job_history(context: JobContext, timestamp: int = 0) -> None:
        """Delete succeeded jobs, and their events, past the retention, using procrastinate's own delete."""
        from app.core.db import job_session
        from app.features.health.service import run_job_pruning

        await run_job_pruning(
            job_session, delete_old_jobs=context.app.job_manager.delete_old_jobs, now=datetime.now(UTC)
        )
