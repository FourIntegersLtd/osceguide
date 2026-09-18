"""Summarising a conversation after it ends, in the background.

Both jobs are enqueued inside the transaction that recorded the thing they are
about, so the work and the record of it being owed commit together — the rule
`attempts/jobs.py` states and ADR 0006 sets.

The session job is the one with teeth: it writes the note and then deletes the
turns, which is how a dashboard conversation stops being a recording of
somebody's screen and becomes a line the tutor can read next time.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import defer_in_transaction, get_jobs_app
from app.core.logging import get_logger
from app.features.tutor_memory import domain

log = get_logger(__name__)

SUMMARIES_QUEUE = "summaries"
SESSION_SUMMARY_TASK = "summarise_assistant_session"
DEBRIEF_SUMMARY_TASK = "summarise_debrief"

INDEX_QUEUE = "material"
REINDEX_TASK = "reindex_material"

# Nightly, not on every publish. Embedding the whole library takes minutes
# and costs money, and material is edited in batches by an author rather
# than continuously — so a fixed run is cheaper than a stampede of them,
# and the admin route is there for when somebody cannot wait for it.
REINDEX_CRON = "17 3 * * *"


async def on_transcript(session: AsyncSession, session_id: uuid.UUID, session_type: str) -> bool:
    """The seam `assistant` calls when a transcript arrives. Returns whether to keep it.

    A dashboard session is kept *and* queued for summarising: the turns are the
    only record until the note exists, so they are stored first and deleted by
    the job that replaces them.
    """
    policy = domain.transcript_policy(session_type)
    if policy is domain.TranscriptPolicy.DISCARD:
        return False
    if policy is domain.TranscriptPolicy.SUMMARISE:
        await defer_in_transaction(
            session,
            queue=SUMMARIES_QUEUE,
            task=SESSION_SUMMARY_TASK,
            queueing_lock=f"session-summary:{session_id}",
            args={"session_id": str(session_id)},
        )
    return True


async def on_interaction_complete(session: AsyncSession, attempt: Any) -> None:
    """The seam `attempts` calls once a transcript is complete and marking is queued."""
    if not domain.should_summarise_attempt(kind=str(attempt.kind), complete=True):
        return
    await defer_in_transaction(
        session,
        queue=SUMMARIES_QUEUE,
        task=DEBRIEF_SUMMARY_TASK,
        queueing_lock=f"debrief-summary:{attempt.id}",
        args={"attempt_id": str(attempt.id)},
    )


def register() -> None:
    """Declare the tasks with procrastinate.

    Behind a function so importing this module for its logic — which the tests
    do — needs no configured queue.
    """
    app = get_jobs_app()

    @app.task(name=SESSION_SUMMARY_TASK, queue=SUMMARIES_QUEUE)
    async def summarise_assistant_session(session_id: str) -> None:
        from app.core.db import job_session
        from app.features.tutor_memory import service_summaries
        from app.features.tutor_memory.summariser import build_summariser

        async with job_session() as session:
            await service_summaries.summarise_assistant_session(
                session, uuid.UUID(session_id), summariser=build_summariser()
            )

    @app.periodic(cron=REINDEX_CRON)
    @app.task(name=REINDEX_TASK, queue=INDEX_QUEUE)
    async def reindex_material(timestamp: int = 0) -> None:
        from app.core.db import job_session
        from app.features.tutor_memory import service_material
        from app.features.tutor_memory.index import build_material_index

        async with job_session() as session:
            await service_material.reindex(session, index=build_material_index(session))

    @app.task(name=DEBRIEF_SUMMARY_TASK, queue=SUMMARIES_QUEUE)
    async def summarise_debrief(attempt_id: str) -> None:
        from app.core.db import job_session
        from app.features.tutor_memory import service_summaries
        from app.features.tutor_memory.summariser import build_summariser

        async with job_session() as session:
            await service_summaries.summarise_debrief(
                session, uuid.UUID(attempt_id), summariser=build_summariser()
            )
