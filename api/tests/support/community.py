"""Helpers for tests that watch the community assistant's queue."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def queued_for(db_session: AsyncSession, post_id: Any) -> list[str]:
    """The task names queued for one post."""
    rows = await db_session.execute(
        text("SELECT task_name FROM procrastinate_jobs WHERE args->>'post_id' = :id"), {"id": str(post_id)}
    )
    return [row[0] for row in rows]
