"""Storage for study material."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
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
    item = MediaItem(
        kind=kind,
        slug=slug,
        title=title,
        summary=summary,
        content=content,
        exam_id=exam_id,
        author_id=author_id,
    )
    session.add(item)
    await session.flush()
    await session.refresh(item)
    return item


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


def _catalog_filters(
    *,
    kind: str | None,
    statuses: tuple[str, ...] | None,
    exam_id: uuid.UUID | None = None,
    search: str | None = None,
) -> list[Any]:
    """The conditions the catalogue narrows by, shared with its count.

    One list rather than two copies of the same clauses, because the count has
    to describe exactly the rows the page came from — a `total_count` that
    ignored a filter would print a bigger number than the filter can ever
    reach.
    """
    conditions: list[Any] = []
    if statuses is None:
        conditions.append(MediaItem.status == "published")
    elif len(statuses) == 1:
        conditions.append(MediaItem.status == statuses[0])
    else:
        conditions.append(MediaItem.status.in_(statuses))
    if kind:
        conditions.append(MediaItem.kind == kind)
    if exam_id is not None:
        # Material tagged with no exam is free material and belongs on every
        # exam's list, which is what the consumer screens already showed: an
        # "all exams" article rail is the free half of the library, not a
        # fifth exam.
        conditions.append(or_(MediaItem.exam_id == exam_id, MediaItem.exam_id.is_(None)))
    term = (search or "").strip()
    if term:
        # Matched like the station library's title filter, including its LIKE
        # wildcards: a `%` typed into a search box widens the query here too.
        conditions.append(or_(MediaItem.title.ilike(f"%{term}%"), MediaItem.summary.ilike(f"%{term}%")))
    return conditions


async def list_catalog(
    session: AsyncSession,
    *,
    kind: str | None,
    statuses: tuple[str, ...] | None,
    limit: int,
    cursor: dict[str, Any] | None = None,
    exam_id: uuid.UUID | None = None,
    search: str | None = None,
) -> tuple[list[MediaItem], str | None]:
    """A page of the catalogue, narrowed by kind, status, exam and a title or summary fragment."""
    stmt = select(MediaItem).where(
        *_catalog_filters(kind=kind, statuses=statuses, exam_id=exam_id, search=search)
    )
    return await keyset_page(
        session,
        stmt,
        sort_col=MediaItem.created_at,
        id_col=MediaItem.id,
        limit=limit,
        cursor=cursor,
    )


async def count_catalog(
    session: AsyncSession,
    *,
    kind: str | None,
    statuses: tuple[str, ...] | None,
    exam_id: uuid.UUID | None = None,
    search: str | None = None,
) -> int:
    """How many items the same filters match, ignoring the cursor."""
    stmt = (
        select(func.count())
        .select_from(MediaItem)
        .where(*_catalog_filters(kind=kind, statuses=statuses, exam_id=exam_id, search=search))
    )
    return int((await session.execute(stmt)).scalar_one())


async def list_published(
    session: AsyncSession,
    *,
    kind: str | None,
    limit: int,
    cursor: dict[str, Any] | None = None,
) -> tuple[list[MediaItem], str | None]:
    return await list_catalog(session, kind=kind, statuses=None, limit=limit, cursor=cursor)


async def delete_item(session: AsyncSession, item_id: uuid.UUID) -> None:
    item = await by_id(session, item_id)
    if item is not None:
        await session.delete(item)
