"""Registers the background jobs a platform admin's production request runs as: checking an
item's facts, writing and checking its script, turning a summary into a podcast, re-rendering a
slide deck's narration, or voicing a podcast script.
"""

from __future__ import annotations

import uuid

from app.core.jobs import get_jobs_app
from app.core.logging import get_logger

log = get_logger(__name__)


def register() -> None:
    """Wires the production tasks into the shared job queue app.

    Each task opens its own database session rather than reusing the request's, since a
    background job runs long after the request that enqueued it has returned.
    """
    app = get_jobs_app()

    @app.task(name="produce_summary_podcast", queue="media")
    async def produce_summary_podcast(media_id: str, requested_by: str) -> None:
        """Turns a summary item's text into a two-host podcast script and voices it."""
        from app.core.db import job_session
        from app.features.media_production.service import run_summary_podcast_job

        async with job_session() as session:
            await run_summary_podcast_job(session, uuid.UUID(media_id), requested_by=uuid.UUID(requested_by))
            log.info("summary podcast produced", media_id=media_id)

    @app.task(name="regenerate_slide_av", queue="media")
    async def regenerate_slide_av(media_id: str, requested_by: str) -> None:
        """Re-renders a slide deck's narrated video after its slides have changed."""
        from app.core.db import job_session
        from app.features.media_production.service import run_slide_av_job

        async with job_session() as session:
            await run_slide_av_job(session, uuid.UUID(media_id), requested_by=uuid.UUID(requested_by))
            log.info("slide av regenerated", media_id=media_id)

    @app.task(name="produce_podcast_audio", queue="media")
    async def produce_podcast_audio(media_id: str, requested_by: str) -> None:
        """Voices a podcast item's script into an audio file."""
        from app.core.db import job_session
        from app.features.media_production.service import run_podcast_audio_job

        async with job_session() as session:
            await run_podcast_audio_job(session, uuid.UUID(media_id), requested_by=uuid.UUID(requested_by))
            log.info("podcast audio produced", media_id=media_id)

    @app.task(name="check_media_facts", queue="media")
    async def check_media_facts(media_id: str, requested_by: str, previous_status: str | None = None) -> None:
        """Checks an item's clinical claims against the guidelines, and the web where they are silent."""
        from app.core.db import job_session
        from app.features.media_production.service import run_fact_check_job

        async with job_session() as session:
            await run_fact_check_job(
                session,
                uuid.UUID(media_id),
                requested_by=uuid.UUID(requested_by),
                previous_status=previous_status,
            )
            log.info("media facts checked", media_id=media_id)

    @app.task(name="write_media_script", queue="media")
    async def write_media_script(media_id: str, requested_by: str, rewrite: bool = False) -> None:
        """Writes what an item will say and checks it against its source, voicing nothing."""
        from app.core.db import job_session
        from app.features.media_production.service import run_script_write_job

        async with job_session() as session:
            await run_script_write_job(
                session, uuid.UUID(media_id), requested_by=uuid.UUID(requested_by), rewrite=rewrite
            )
            log.info("media script written", media_id=media_id)
