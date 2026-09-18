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
        """Pair whoever is waiting, in every room of every exam.

        Periodic rather than triggered on join: two people arriving at the same
        moment would otherwise both try to match, and one of them would find an
        empty queue.

        Rooms are walked separately. Matching an exam as one pool would pair a
        trainee waiting inside their institution with a stranger, which is the
        thing an audience exists to prevent.
        """
        from app.core.db import job_session
        from app.features.catalog import service as catalog
        from app.features.peer_practice import repository
        from app.features.peer_practice.service import match_waiting

        async with job_session() as session:
            for exam in await catalog.exam_refs(session):
                for audience in await repository.waiting_audiences(session, exam.id):
                    while await match_waiting(session, exam.id, audience=audience) is not None:
                        log.info("practice pair matched", exam=exam.code, room=str(audience.visibility))
