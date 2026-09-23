"""Turning `Post` rows into `PostRead`, for one row or a whole page.

Split out of `service.py`, which keeps the writes and the visibility rules. The
projection is the only place that knows a page fetches its counts and its author
names together rather than per row, and it has no opinion about who may ask;
keeping the two apart is what holds the slice under the shape guard's cap.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import AudienceOut
from app.features.community import repository
from app.features.community.models import Post
from app.features.community.schemas import PostRead
from app.features.identity import service as identity


async def read_one(session: AsyncSession, row: Post, *, viewer_id: uuid.UUID) -> PostRead:
    return (await read_many(session, [row], viewer_id=viewer_id))[0]


async def read_many(session: AsyncSession, rows: list[Post], *, viewer_id: uuid.UUID) -> list[PostRead]:
    """Counts and names fetched for the whole page at once rather than per row."""
    ids = [r.id for r in rows]
    counts, mine = await repository.like_counts(session, ids, viewer_id)
    replies = await repository.reply_counts(session, ids)
    people = await identity.user_refs_by_ids(session, list({r.author_id for r in rows}))
    return [
        PostRead(
            id=r.id,
            kind=r.kind,
            parent_id=r.parent_id,
            author_id=r.author_id,
            # Null when the account is gone. Falling back to the id prints a
            # uuid where a name belongs.
            author_name=people[r.author_id].name if r.author_id in people else None,
            title=r.title,
            body=r.body,
            audience=AudienceOut.of(r),
            like_count=counts.get(r.id, 0),
            liked_by_me=r.id in mine,
            reply_count=replies.get(r.id, 0),
            created_at=r.created_at,
        )
        for r in rows
    ]
