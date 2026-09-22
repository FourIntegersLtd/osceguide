"""Storage for CVs. Mapped classes do not leave this module."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.cv.domain import Status
from app.features.cv.models import Cv


async def create(
    session: AsyncSession, *, user_id: uuid.UUID, original_filename: str, extracted_text: str
) -> Cv:
    """A row in `processing`, written before the model is asked anything."""
    row = Cv(
        user_id=user_id,
        original_filename=original_filename,
        extracted_text=extracted_text,
        status=Status.PROCESSING.value,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def get(session: AsyncSession, cv_id: uuid.UUID) -> Cv | None:
    return (await session.execute(select(Cv).where(Cv.id == cv_id))).scalar_one_or_none()


async def list_for_user(session: AsyncSession, user_id: uuid.UUID, *, limit: int) -> Sequence[Cv]:
    """A person's own CVs, most recent first.

    `created_at` is the upload time; ordering by it and cutting at `limit` is
    what the retiring backend did in Python after fetching all of them.
    """
    stmt = select(Cv).where(Cv.user_id == user_id).order_by(Cv.created_at.desc()).limit(limit)
    return (await session.execute(stmt)).scalars().all()


async def mark_completed(
    session: AsyncSession, cv_id: uuid.UUID, *, structured: dict[str, Any], at: datetime
) -> None:
    await session.execute(
        update(Cv)
        .where(Cv.id == cv_id)
        .values(status=Status.COMPLETED.value, structured=structured, completed_at=at, error=None)
    )


async def mark_failed(session: AsyncSession, cv_id: uuid.UUID, *, error: str, at: datetime) -> None:
    await session.execute(
        update(Cv).where(Cv.id == cv_id).values(status=Status.FAILED.value, error=error, completed_at=at)
    )
