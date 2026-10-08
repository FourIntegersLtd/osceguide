"""The queue looking after itself."""

from __future__ import annotations

from app.core.jobs import get_jobs_app
from app.core.logging import get_logger

log = get_logger(__name__)


def register() -> None:
    """Wire up health's background jobs on the shared jobs app."""
    app = get_jobs_app()

    @app.periodic(cron="*/5 * * * *")
    @app.task(name="reclaim_stalled_jobs", queue="health")
    async def reclaim_stalled_jobs(timestamp: int = 0) -> None:
        """Requeue or fail the jobs a dead worker left `doing`, every five minutes."""
        from app.core.db import job_session
        from app.features.health.service import reclaim_stalled_jobs as run

        async with job_session() as session:
            requeued, failed = await run(session)
            if failed:
                # An error, so it reaches Sentry: a job that failed here will not run again (S-25).
                log.error("stalled jobs failed", requeued=requeued, failed=failed)
            elif requeued:
                log.warning("stalled jobs requeued", requeued=requeued)
