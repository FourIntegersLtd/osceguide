"""Storage for study material."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import encode_cursor
from app.features.media.models import MediaItem


async def create(
    session: AsyncSession,
    *,
    kind: str,
    slug: str,
    title: str,
    summary: str | None,
    content: dict[str, Any],
    exam_id: uuid.UUID | None,
    author_id: uuid.UUID | None,
) -> MediaItem:
    row = MediaItem(
        kind=kind,
        slug=slug,
        title=title,
        summary=summary,
        content=content,
        exam_id=exam_id,
        author_id=author_id,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def by_id(session: AsyncSession, item_id: uuid.UUID) -> MediaItem | None:
    return (await session.execute(select(MediaItem).where(MediaItem.id == item_id))).scalar_one_or_none()


async def by_slug(session: AsyncSession, slug: str) -> MediaItem | None:
    return (await session.execute(select(MediaItem).where(MediaItem.slug == slug))).scalar_one_or_none()


async def by_ids(session: AsyncSession, item_ids: list[uuid.UUID]) -> list[MediaItem]:
    if not item_ids:
        return []
    stmt = select(MediaItem).where(MediaItem.id.in_(item_ids))
    return list((await session.execute(stmt)).scalars())


async def update_item(session: AsyncSession, item_id: uuid.UUID, **values: Any) -> None:
    await session.execute(update(MediaItem).where(MediaItem.id == item_id).values(**values))


async def list_published(
    session: AsyncSession,
    *,
    kind: str | None,
    limit: int,
    cursor: dict[str, Any] | None = None,
) -> tuple[list[MediaItem], str | None]:
    stmt = select(MediaItem).where(MediaItem.status == "published")
    if kind:
        stmt = stmt.where(MediaItem.kind == kind)
    if cursor:
        stmt = stmt.where(MediaItem.created_at < datetime.fromisoformat(cursor["t"]))
    rows = list(
        (
            await session.execute(
                stmt.order_by(MediaItem.created_at.desc(), MediaItem.id.desc()).limit(limit + 1)
            )
        ).scalars()
    )
    if len(rows) <= limit:
        return rows, None
    page = rows[:limit]
    return page, encode_cursor({"t": page[-1].created_at, "i": str(page[-1].id)})
