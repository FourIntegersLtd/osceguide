"""Community use cases."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
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
from app.features.identity import service as identity
from app.features.stations import service as stations

_REFUSALS: dict[type[Exception], type[AppError]] = {
    domain.NotYours: errors.NotYoursError,
    domain.EmptyContent: errors.EmptyContentError,
    domain.ContentTooLong: errors.ContentTooLongError,
    domain.TagTooLong: errors.TagTooLongError,
    domain.TooManyTags: errors.TooManyTagsError,
}


async def ask(
    session: AsyncSession,
    *,
    author_id: uuid.UUID,
    title: str,
    body: str,
    exam_code: str | None,
    audience: Audience = PUBLIC,
    tags: list[str] | None = None,
) -> PostRead:
    """Ask a new question, in the given room and tagged for the feed filter."""
    try:
        domain.ensure_postable(body)
        # A question is what tags describe: they are how the feed is narrowed.
        # A reply is never given its own, for the reason it is never given its
        # own audience — it belongs to its question's thread and topic.
        cleaned_tags = domain.clean_tags(tags or [])
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)
    ensure_may_address(audience, await audiences_for(session, author_id))

    exam_id = None
    if exam_code:
        exam_id = (await resolve_exam(session, exam_code)).id

    question = await repository.create_post(
        session,
        kind="question",
        author_id=author_id,
        title=domain.clean(title),
        body=domain.clean(body),
        exam_id=exam_id,
        audience=audience,
        tags=cleaned_tags,
    )
    return await read_one(session, question, viewer_id=author_id)


async def reply(session: AsyncSession, parent_id: uuid.UUID, *, author_id: uuid.UUID, body: str) -> PostRead:
    """Answer a question, in the same room as the question itself."""
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

    created_reply = await repository.create_post(
        session,
        kind="reply",
        author_id=author_id,
        body=domain.clean(body),
        parent_id=parent_id,
        exam_id=parent.exam_id,
        audience=audience,
    )
    return await read_one(session, created_reply, viewer_id=author_id)


async def comment_on_station(
    session: AsyncSession,
    station_id: uuid.UUID,
    *,
    author_id: uuid.UUID,
    body: str,
    audience: Audience = PUBLIC,
) -> PostRead:
    """Leave a comment on a station, in the given room."""
    # Asked before the insert rather than mapped off its failure: the foreign
    # key would refuse a station that does not exist, and an unmapped
    # IntegrityError answers `internal_error` (S3).
    if not await stations.station_exists(session, station_id):
        raise errors.StationNotFound()
    try:
        domain.ensure_postable(body)
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)
    ensure_may_address(audience, await audiences_for(session, author_id))
    comment = await repository.create_post(
        session,
        kind="comment",
        author_id=author_id,
        body=domain.clean(body),
        parent_id=None,
        station_id=station_id,
        audience=audience,
    )
    return await read_one(session, comment, viewer_id=author_id)


async def remove(
    session: AsyncSession,
    post_id: uuid.UUID,
    *,
    actor_id: uuid.UUID,
    actor_is_admin: bool,
    moderates_org_ids: frozenset[uuid.UUID],
    now: datetime,
) -> None:
    """Soft-remove a post: your own, any platform moderator's, or one inside a room you administer."""
    post = await repository.post_by_id(session, post_id)
    if post is None:
        raise errors.PostNotFound()
    try:
        domain.ensure_removable(
            author_id=str(post.author_id),
            actor_id=str(actor_id),
            actor_is_admin=actor_is_admin,
            # An institution moderates what is addressed inside it, which is
            # the whole of what org and group audiences are for.
            actor_moderates_audience=post.audience_org_id in moderates_org_ids,
        )
    except domain.NotYours as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.remove_post(session, post_id, at=now, by=actor_id)


async def set_like(session: AsyncSession, post_id: uuid.UUID, *, user_id: uuid.UUID, liked: bool) -> PostRead:
    """Like or unlike a post. Idempotent both ways: liking twice is still one like."""
    post = await repository.post_by_id(session, post_id)
    if post is None:
        raise errors.PostNotFound()
    # SEC-020: mirror the audience gate that question_detail / list_replies use,
    # so a post outside the viewer's audience cannot be liked (or probed by id
    # via a like succeeding). Indistinguishable from a post that does not exist.
    if not can_see(audience_of(post), await audiences_for(session, user_id)):
        raise errors.PostNotFound()
    await repository.set_like(session, post_id, user_id, liked=liked)
    return await read_one(session, post, viewer_id=user_id)


async def list_questions(
    session: AsyncSession,
    *,
    viewer_id: uuid.UUID,
    limit: int,
    cursor: dict[str, Any] | None,
    audience: Audience | None = None,
    mine: bool = False,
    tag: str | None = None,
) -> tuple[list[PostRead], str | None]:
    """Questions this viewer may see, newest first, narrowed by room, author or tag."""
    viewer = await audiences_for(session, viewer_id)
    questions, next_cursor = await repository.list_questions(
        session,
        viewer=viewer,
        limit=limit,
        cursor=cursor,
        audience=audience,
        author_id=viewer_id if mine else None,
        # Normalized the way tags are stored, so "Cardiology" finds
        # "cardiology". A blank filter is no filter.
        tag=domain.normalize_tag(tag) if tag else None,
    )
    return await read_many(session, questions, viewer_id=viewer_id), next_cursor


async def question_detail(session: AsyncSession, question_id: uuid.UUID, *, viewer_id: uuid.UUID) -> PostRead:
    """One question, by id.

    There was no read for a single question, only the paged feed, so a thread
    was found by searching the page the feed already served — which meant a
    question older than the first hundred opened as "not found". Same
    visibility rule as the replies beneath it: something the viewer may not see
    answers the same as something that does not exist.
    """
    question = await repository.post_by_id(session, question_id)
    if question is None or question.kind != "question":
        raise errors.PostNotFound()
    if not can_see(audience_of(question), await audiences_for(session, viewer_id)):
        raise errors.PostNotFound()
    return await read_one(session, question, viewer_id=viewer_id)


async def list_my_answers(
    session: AsyncSession,
    *,
    viewer_id: uuid.UUID,
    limit: int,
    cursor: dict[str, Any] | None,
) -> tuple[list[PostRead], str | None]:
    """This person's own replies, across every question they have answered."""
    viewer = await audiences_for(session, viewer_id)
    replies, next_cursor = await repository.list_answers(
        session, viewer=viewer, author_id=viewer_id, limit=limit, cursor=cursor
    )
    return await read_many(session, replies, viewer_id=viewer_id), next_cursor


async def list_replies(
    session: AsyncSession, parent_id: uuid.UUID, *, viewer_id: uuid.UUID
) -> list[PostRead]:
    """Every reply under one question, if the viewer may see the question at all."""
    parent = await repository.post_by_id(session, parent_id)
    if parent is None:
        raise errors.PostNotFound()
    if not can_see(audience_of(parent), await audiences_for(session, viewer_id)):
        # Indistinguishable from a question that does not exist, so a private
        # thread cannot be probed by id.
        raise errors.PostNotFound()
    replies = await repository.list_children(session, parent_id)
    return await read_many(session, replies, viewer_id=viewer_id)


async def list_station_comments(
    session: AsyncSession, station_id: uuid.UUID, *, viewer_id: uuid.UUID
) -> list[PostRead]:
    """Comments on one station that this viewer may see."""
    viewer = await audiences_for(session, viewer_id)
    comments = await repository.list_station_comments(session, station_id, viewer=viewer)
    return await read_many(session, comments, viewer_id=viewer_id)


async def list_moderation_queue(
    session: AsyncSession, *, viewer_id: uuid.UUID, days: int = 7, limit: int = 100
) -> list[PostRead]:
    """Every post from the last few days, newest first, for a moderator to review."""
    since = datetime.now(tz=UTC) - timedelta(days=days)
    posts = await repository.list_recent_for_moderation(session, since=since, limit=limit)
    return await read_many(session, posts, viewer_id=viewer_id)


# --- Turning `Post` posts into `PostRead`, for one post or a whole page.


async def read_one(session: AsyncSession, post: Post, *, viewer_id: uuid.UUID) -> PostRead:
    return (await read_many(session, [post], viewer_id=viewer_id))[0]


async def read_many(session: AsyncSession, posts: list[Post], *, viewer_id: uuid.UUID) -> list[PostRead]:
    """Counts and names fetched for the whole page at once rather than per post."""
    ids = [post.id for post in posts]
    counts, mine = await repository.like_counts(session, ids, viewer_id)
    reply_counts = await repository.reply_counts(session, ids)
    people = await identity.user_refs_by_ids(session, list({post.author_id for post in posts}))
    return [
        PostRead(
            id=post.id,
            kind=post.kind,
            parent_id=post.parent_id,
            author_id=post.author_id,
            # Null when the account is gone. Falling back to the id prints a
            # uuid where a name belongs.
            author_name=people[post.author_id].name if post.author_id in people else None,
            title=post.title,
            body=post.body,
            # `or []` for a row written before tags existed and read back
            # NULL by a driver, though the column default says that cannot
            # happen: a None here would fail the schema instead of reading
            # as the empty list it means.
            tags=list(post.tags or []),
            audience=AudienceOut.from_row(post),
            like_count=counts.get(post.id, 0),
            liked_by_me=post.id in mine,
            reply_count=reply_counts.get(post.id, 0),
            created_at=post.created_at,
        )
        for post in posts
    ]
