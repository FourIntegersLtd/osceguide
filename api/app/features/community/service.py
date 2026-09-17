"""Community use cases."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import (
    PUBLIC,
    Audience,
    AudienceOut,
    audience_of,
    audiences_for,
    can_see,
    ensure_may_address,
)
from app.core.errors import AppError, raise_mapped
from app.features.catalog.service import resolve_exam
from app.features.community import domain, errors, repository
from app.features.community.models import Post
from app.features.community.schemas import PostRead

_REFUSALS: dict[type[Exception], type[AppError]] = {
    domain.NotYours: errors.NotYoursError,
    domain.EmptyContent: errors.EmptyContentError,
    domain.ContentTooLong: errors.ContentTooLongError,
}


async def ask(
    session: AsyncSession,
    *,
    author_id: uuid.UUID,
    title: str,
    body: str,
    exam_code: str | None,
    audience: Audience = PUBLIC,
) -> PostRead:
    try:
        domain.ensure_postable(body)
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)
    ensure_may_address(audience, await audiences_for(session, author_id))

    exam_id = None
    if exam_code:
        exam_id = (await resolve_exam(session, exam_code)).id

    row = await repository.create_post(
        session,
        kind="question",
        author_id=author_id,
        title=domain.clean(title),
        body=domain.clean(body),
        exam_id=exam_id,
        audience=audience,
    )
    return await _read_one(session, row, viewer_id=author_id)


async def reply(session: AsyncSession, parent_id: uuid.UUID, *, author_id: uuid.UUID, body: str) -> PostRead:
    parent = await repository.post_by_id(session, parent_id)
    if parent is None:
        raise errors.PostNotFound()
    # A reply inherits the question's audience and is never given its own.
    # Letting a reply be addressed separately is how a private thread leaks:
    # one public answer quoting the question publishes it.
    audience = audience_of(parent)
    viewer = await audiences_for(session, author_id)
    if not can_see(audience, viewer):
        raise errors.PostNotFound()
    try:
        domain.ensure_postable(body)
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)

    row = await repository.create_post(
        session,
        kind="reply",
        author_id=author_id,
        body=domain.clean(body),
        parent_id=parent_id,
        exam_id=parent.exam_id,
        audience=audience,
    )
    return await _read_one(session, row, viewer_id=author_id)


async def comment_on_station(
    session: AsyncSession,
    station_id: uuid.UUID,
    *,
    author_id: uuid.UUID,
    body: str,
    audience: Audience = PUBLIC,
) -> PostRead:
    try:
        domain.ensure_postable(body)
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)
    ensure_may_address(audience, await audiences_for(session, author_id))
    row = await repository.create_post(
        session,
        kind="comment",
        author_id=author_id,
        body=domain.clean(body),
        parent_id=None,
        station_id=station_id,
        audience=audience,
    )
    return await _read_one(session, row, viewer_id=author_id)


async def remove(
    session: AsyncSession,
    post_id: uuid.UUID,
    *,
    actor_id: uuid.UUID,
    actor_is_admin: bool,
    moderates_org_ids: frozenset[uuid.UUID],
    now: datetime,
) -> None:
    row = await repository.post_by_id(session, post_id)
    if row is None:
        raise errors.PostNotFound()
    try:
        domain.ensure_removable(
            author_id=str(row.author_id),
            actor_id=str(actor_id),
            actor_is_admin=actor_is_admin,
            # An institution moderates what is addressed inside it, which is
            # the whole of what org and group audiences are for.
            actor_moderates_audience=row.audience_org_id in moderates_org_ids,
        )
    except domain.NotYours as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.remove_post(session, post_id, at=now, by=actor_id)


async def set_like(session: AsyncSession, post_id: uuid.UUID, *, user_id: uuid.UUID, liked: bool) -> PostRead:
    row = await repository.post_by_id(session, post_id)
    if row is None:
        raise errors.PostNotFound()
    await repository.set_like(session, post_id, user_id, liked=liked)
    return await _read_one(session, row, viewer_id=user_id)


async def list_questions(
    session: AsyncSession,
    *,
    viewer_id: uuid.UUID,
    limit: int,
    cursor: dict[str, Any] | None,
    audience: Audience | None = None,
) -> tuple[list[PostRead], str | None]:
    viewer = await audiences_for(session, viewer_id)
    rows, next_cursor = await repository.list_questions(
        session, viewer=viewer, limit=limit, cursor=cursor, audience=audience
    )
    return await _read_many(session, rows, viewer_id=viewer_id), next_cursor


async def list_replies(
    session: AsyncSession, parent_id: uuid.UUID, *, viewer_id: uuid.UUID
) -> list[PostRead]:
    parent = await repository.post_by_id(session, parent_id)
    if parent is None:
        raise errors.PostNotFound()
    if not can_see(audience_of(parent), await audiences_for(session, viewer_id)):
        # Indistinguishable from a question that does not exist, so a private
        # thread cannot be probed by id.
        raise errors.PostNotFound()
    rows = await repository.list_children(session, parent_id)
    return await _read_many(session, rows, viewer_id=viewer_id)


async def list_station_comments(
    session: AsyncSession, station_id: uuid.UUID, *, viewer_id: uuid.UUID
) -> list[PostRead]:
    viewer = await audiences_for(session, viewer_id)
    rows = await repository.list_station_comments(session, station_id, viewer=viewer)
    return await _read_many(session, rows, viewer_id=viewer_id)


async def _read_one(session: AsyncSession, row: Post, *, viewer_id: uuid.UUID) -> PostRead:
    return (await _read_many(session, [row], viewer_id=viewer_id))[0]


async def _read_many(session: AsyncSession, rows: list[Post], *, viewer_id: uuid.UUID) -> list[PostRead]:
    """Counts fetched for the whole page at once rather than per row."""
    ids = [r.id for r in rows]
    counts, mine = await repository.like_counts(session, ids, viewer_id)
    replies = await repository.reply_counts(session, ids)
    return [
        PostRead(
            id=r.id,
            kind=r.kind,
            parent_id=r.parent_id,
            author_id=r.author_id,
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
