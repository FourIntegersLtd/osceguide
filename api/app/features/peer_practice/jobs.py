"""Matching people who are waiting."""

from __future__ import annotations

from app.core.jobs import get_jobs_app
from app.core.logging import get_logger

log = get_logger(__name__)


def register() -> None:
    app = get_jobs_app()

    @app.periodic(cron="* * * * *")
    @app.task(name="match_practice_queue", queue="matching")
    async def match_practice_queue(timestamp: int = 0) -> None:
        """Pair whoever is waiting, for every exam.

        Periodic rather than triggered on join: two people arriving at the same
        moment would otherwise both try to match, and one of them would find an
        empty queue.
        """
        from app.core.db import job_session
        from app.features.catalog import repository as catalog_repo
        from app.features.peer_practice.service import match_waiting

        async with job_session() as session:
            for exam in await catalog_repo.list_exams(session):
                while await match_waiting(session, exam.id) is not None:
                    log.info("practice pair matched", exam=exam.code)
