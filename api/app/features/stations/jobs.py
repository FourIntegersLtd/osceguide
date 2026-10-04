"""The background jobs that draft a template and a station from an uploaded document, and that
check a platform station's facts.

Enqueued in the same transaction as the row they concern (ADR 0006): either the
import row and its job both land or neither does. The model calls run here
rather than in the request, so a slow model is a slow job and not a slow upload.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import defer_in_transaction, get_jobs_app
from app.core.logging import get_logger
from app.core.settings import get_settings

log = get_logger(__name__)

QUEUE = "station_imports"
TEMPLATE_TASK = "draft_import_template"
STATION_TASK = "draft_import_station"
FACTS_TASK = "check_station_facts"


async def enqueue_template_draft(session: AsyncSession, *, import_id: uuid.UUID) -> None:
    """Queue drafting a template from one import. The queueing lock makes a redelivery idempotent."""
    await defer_in_transaction(
        session,
        queue=QUEUE,
        task=TEMPLATE_TASK,
        args={"import_id": str(import_id)},
        queueing_lock=f"station-import:{import_id}:template",
    )


async def enqueue_station_draft(session: AsyncSession, *, import_id: uuid.UUID) -> None:
    """Queue drafting a station from one import. The queueing lock makes a redelivery idempotent."""
    await defer_in_transaction(
        session,
        queue=QUEUE,
        task=STATION_TASK,
        args={"import_id": str(import_id)},
        queueing_lock=f"station-import:{import_id}:station",
    )


async def enqueue_fact_check(
    session: AsyncSession, *, version_id: uuid.UUID, requested_by: uuid.UUID
) -> None:
    """Queue checking one version's facts. The queueing lock keeps it to one run at a time."""
    await defer_in_transaction(
        session,
        queue=QUEUE,
        task=FACTS_TASK,
        args={"version_id": str(version_id), "requested_by": str(requested_by)},
        queueing_lock=f"station-version:{version_id}:facts",
    )


def register() -> None:
    """Attach the import and fact check tasks to the jobs app, so the worker picks them up."""
    app = get_jobs_app()

    @app.task(name=TEMPLATE_TASK, queue=QUEUE)
    async def draft_import_template(import_id: str) -> None:
        """Draft a template from one queued import and log that it finished."""
        from app.core.db import job_session
        from app.features.stations.service_imports import run_template_job

        async with job_session() as session:
            await run_template_job(session, uuid.UUID(import_id), settings=get_settings())
            log.info("station import template drafted", import_id=import_id)

    @app.task(name=STATION_TASK, queue=QUEUE)
    async def draft_import_station(import_id: str) -> None:
        """Draft a station from one queued import and log that it finished."""
        from app.core.db import job_session
        from app.features.stations.service_imports import run_station_job

        async with job_session() as session:
            await run_station_job(session, uuid.UUID(import_id), settings=get_settings())
            log.info("station import station drafted", import_id=import_id)

    @app.task(name=FACTS_TASK, queue=QUEUE)
    async def check_station_facts(version_id: str, requested_by: str) -> None:
        """Check one platform station version's clinical claims and keep the result on it."""
        from app.core.db import job_session
        from app.features.stations.service_facts import run_check

        async with job_session() as session:
            await run_check(session, uuid.UUID(version_id), requested_by=uuid.UUID(requested_by))
            log.info("station facts checked", version_id=version_id)
