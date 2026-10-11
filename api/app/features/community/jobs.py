"""Community's background work: the assistant answering questions nobody has."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.jobs import get_jobs_app
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.features.assistant.service_community import help_drafter as draft_reply

log = get_logger(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC)


def register() -> None:
    """Wire up community's background jobs on the shared jobs app."""
    app = get_jobs_app()

    @app.periodic(cron="*/10 * * * *")
    @app.task(name="reply_as_assistant", queue="community")
    async def reply_as_assistant(timestamp: int = 0) -> None:
        """Answer each unanswered general or platform question as the OSCE Guide assistant.

        A no-op while `COMMUNITY_ASSISTANT_REPLIES` is unset. A draft that fails ends the run: the
        queue row fails in `/platform/jobs` for staff to retry, and the question stays unanswered.
        """
        settings = get_settings()
        if not settings.community_assistant_replies:
            return
        from app.core.db import job_session
        from app.features.community import service

        async with job_session() as session:
            posted = await service.reply_as_assistant(session, draft=draft_reply(settings), now=utcnow())
            if posted:
                log.info("assistant replies posted", count=posted)
