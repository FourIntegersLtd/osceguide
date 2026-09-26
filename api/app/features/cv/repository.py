"""Storage for CVs. Mapped classes do not leave this module."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.cv.domain import Status
from app.features.cv.models import Cv


async def create(
    session: AsyncSession, *, user_id: uuid.UUID, original_filename: str, extracted_text: str
) -> Cv:
    """A row in `processing`, written before the model is asked anything."""
    cv = Cv(
        user_id=user_id,
        original_filename=original_filename,
        extracted_text=extracted_text,
        status=Status.PROCESSING.value,
    )
    session.add(cv)
    await session.flush()
    await session.refresh(cv)
    return cv


async def get(session: AsyncSession, cv_id: uuid.UUID) -> Cv | None:
    return (await session.execute(select(Cv).where(Cv.id == cv_id))).scalar_one_or_none()


async def list_for_user(session: AsyncSession, user_id: uuid.UUID, *, limit: int) -> Sequence[Cv]:
    """A person's own CVs, most recent first, by upload time (`created_at`)."""
    stmt = select(Cv).where(Cv.user_id == user_id).order_by(Cv.created_at.desc()).limit(limit)
    return (await session.execute(stmt)).scalars().all()


async def delete_cv(session: AsyncSession, cv_id: uuid.UUID, user_id: uuid.UUID) -> int:
    """Delete one CV of this person's, and say whether there was one to delete.

    The owner is in the WHERE clause rather than checked beforehand, so a delete
    cannot reach somebody else's row and "not yours" and "not there" come back
    as the same zero — which is what lets the service answer both alike.
    """
    deletion = await session.execute(delete(Cv).where(Cv.id == cv_id, Cv.user_id == user_id))
    return int(getattr(deletion, "rowcount", 0) or 0)


async def mark_completed(
    session: AsyncSession, cv_id: uuid.UUID, *, structured: dict[str, Any], at: datetime
) -> None:
    """Record a CV's read-out sections and clear any earlier error."""
    await session.execute(
        update(Cv)
        .where(Cv.id == cv_id)
        .values(status=Status.COMPLETED.value, structured=structured, completed_at=at, error=None)
    )


async def mark_failed(session: AsyncSession, cv_id: uuid.UUID, *, error: str, at: datetime) -> None:
    """Record why a CV's reading job failed, so the person sees the reason instead of a stuck row."""
    await session.execute(
        update(Cv).where(Cv.id == cv_id).values(status=Status.FAILED.value, error=error, completed_at=at)
    )
