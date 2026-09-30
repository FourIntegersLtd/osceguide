"""Hands an AV production job to procrastinate, the background job queue every worker polls."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def defer_job(
    session: AsyncSession,
    *,
    queue: str,
    task: str,
    args: dict[str, Any],
    queueing_lock: str,
) -> None:
    """Enqueues a background task, refusing a second one under the same lock while one is running."""
    await session.execute(
        text(
            "SELECT procrastinate_defer_jobs_v1(ARRAY[ROW("
            ":queue, :task, :priority, NULL, :queueing_lock, CAST(:args AS jsonb), NULL"
            ")]::procrastinate_job_to_defer_v1[])"
        ),
        {
            "queue": queue,
            "task": task,
            "priority": 0,
            "queueing_lock": queueing_lock,
            "args": json.dumps(args),
        },
    )


def lock_for_media(media_id: uuid.UUID, operation: str) -> str:
    """The queueing lock key that stops the same item's same production operation running twice at once."""
    return f"media_av:{media_id}:{operation}"
