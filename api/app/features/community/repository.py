"""Storage for community posts and likes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import Audience, ViewerAudiences, addressed_to, visible_to
from app.core.pagination import keyset_page
from app.features.community.models import Post, PostLike


async def create_post(
    session: AsyncSession,
    *,
    kind: str,
    author_id: uuid.UUID,
    body: str,
    audience: Audience,
    title: str | None = None,
    parent_id: uuid.UUID | None = None,
    exam_id: uuid.UUID | None = None,
    station_id: uuid.UUID | None = None,
) -> Post:
    row = Post(
        kind=kind,
        author_id=author_id,
        body=body,
        title=title,
        parent_id=parent_id,
        exam_id=exam_id,
        station_id=station_id,
        visibility=str(audience.visibility),
        audience_org_id=audience.org_id,
        audience_group_id=audience.group_id,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def post_by_id(session: AsyncSession, post_id: uuid.UUID) -> Post | None:
    stmt = select(Post).where(Post.id == post_id, Post.removed_at.is_(None))
    return (await session.execute(stmt)).scalar_one_or_none()


async def remove_post(session: AsyncSession, post_id: uuid.UUID, *, at: datetime, by: uuid.UUID) -> None:
    """Soft-removed, so a thread does not lose its shape when one reply goes."""
    await session.execute(update(Post).where(Post.id == post_id).values(removed_at=at, removed_by=by))


async def list_questions(
    session: AsyncSession,
    *,
    viewer: ViewerAudiences,
    limit: int,
    cursor: dict[str, Any] | None = None,
    exam_id: uuid.UUID | None = None,
    audience: Audience | None = None,
) -> tuple[list[Post], str | None]:
    """Questions this viewer may see, newest first.

    The audience filter is applied here rather than after the fetch: filtering
    a page in Python would return short pages and, worse, page *past* content
    the viewer cannot see.
    """
    stmt = select(Post).where(Post.kind == "question", Post.removed_at.is_(None), visible_to(Post, viewer))
    if exam_id is not None:
        stmt = stmt.where(Post.exam_id == exam_id)
    if audience is not None:
        # Narrowing to one room, on top of everything the viewer may see.
        stmt = stmt.where(addressed_to(Post, audience))
    return await keyset_page(
        session, stmt, sort_col=Post.created_at, id_col=Post.id, limit=limit, cursor=cursor
    )


async def list_children(session: AsyncSession, parent_id: uuid.UUID) -> list[Post]:
    stmt = (
        select(Post).where(Post.parent_id == parent_id, Post.removed_at.is_(None)).order_by(Post.created_at)
    )
    return list((await session.execute(stmt)).scalars())


async def list_station_comments(
    session: AsyncSession, station_id: uuid.UUID, *, viewer: ViewerAudiences
) -> list[Post]:
    stmt = (
        select(Post)
        .where(Post.station_id == station_id, Post.removed_at.is_(None), visible_to(Post, viewer))
        .order_by(Post.created_at)
    )
    return list((await session.execute(stmt)).scalars())


async def set_like(session: AsyncSession, post_id: uuid.UUID, user_id: uuid.UUID, *, liked: bool) -> None:
    """Idempotent both ways: liking twice is one like, unliking twice is none."""
    if liked:
        existing = await session.execute(
            select(PostLike).where(PostLike.post_id == post_id, PostLike.user_id == user_id)
        )
        if existing.scalar_one_or_none() is None:
            session.add(PostLike(post_id=post_id, user_id=user_id))
            await session.flush()
        return
    await session.execute(delete(PostLike).where(PostLike.post_id == post_id, PostLike.user_id == user_id))


async def like_counts(
    session: AsyncSession, post_ids: list[uuid.UUID], viewer_id: uuid.UUID
) -> tuple[dict[uuid.UUID, int], set[uuid.UUID]]:
    """Counts and the viewer's own likes, in two queries rather than per post."""
    if not post_ids:
        return {}, set()
    counts = {
        row[0]: row[1]
        for row in (
            await session.execute(
                select(PostLike.post_id, func.count(PostLike.id))
                .where(PostLike.post_id.in_(post_ids))
                .group_by(PostLike.post_id)
            )
        ).all()
    }
    mine = set(
        (
            await session.execute(
                select(PostLike.post_id).where(PostLike.post_id.in_(post_ids), PostLike.user_id == viewer_id)
            )
        ).scalars()
    )
    return counts, mine


async def reply_counts(session: AsyncSession, post_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not post_ids:
        return {}
    rows = (
        await session.execute(
            select(Post.parent_id, func.count(Post.id))
            .where(Post.parent_id.in_(post_ids), Post.removed_at.is_(None))
            .group_by(Post.parent_id)
        )
    ).all()
    return {row[0]: row[1] for row in rows}
