"""Community's background work: the assistant answering a question when it is asked."""

from __future__ import annotations

import uuid

from app.core.jobs import get_jobs_app
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.features.assistant.service_community import help_drafter as draft_reply
from app.features.community import domain

log = get_logger(__name__)


def register() -> None:
    """Wire up community's background jobs on the shared jobs app."""
    app = get_jobs_app()

    @app.task(name=domain.ASSISTANT_TASK, queue=domain.ASSISTANT_QUEUE)
    async def reply_as_assistant(post_id: str) -> None:
        """Answer one general or platform question as the OSCE Guide assistant, queued by `ask`.

        A draft that fails (no `OPENAI_API_KEY` included) ends the run: the queue row fails in
        `/platform/jobs` for staff to retry, and the question stays unanswered.
        """
        from app.core.db import job_session
        from app.features.community import service

        async with job_session() as session:
            posted = await service.reply_as_assistant(
                session, uuid.UUID(post_id), draft=draft_reply(get_settings())
            )
            if posted:
                log.info("assistant reply posted", post_id=post_id)
