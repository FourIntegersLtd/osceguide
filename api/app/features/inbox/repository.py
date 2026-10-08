"""Storage for in-app messages and who has read them."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Select, and_, column, delete, func, or_, select, table
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorParams, keyset_page
from app.features.inbox.domain import Kind
from app.features.inbox.models import UserMessage, UserMessageRead


async def add_message(
    session: AsyncSession,
    *,
    recipient_user_id: uuid.UUID | None,
    sender_user_id: uuid.UUID | None,
    kind: Kind,
    subject: str,
    body: str,
    station_flag_id: uuid.UUID | None = None,
    site_message_id: uuid.UUID | None = None,
) -> UserMessage:
    """Store one message, to a person or (with no recipient) to everybody."""
    message = UserMessage(
        recipient_user_id=recipient_user_id,
        sender_user_id=sender_user_id,
        kind=kind,
        subject=subject,
        body=body,
        station_flag_id=station_flag_id,
        site_message_id=site_message_id,
    )
    session.add(message)
    await session.flush()
    await session.refresh(message)
    return message


# `users` as a bare table: this slice reads one column of it and imports no other slice's models.
_USERS = table("users", column("id"), column("created_at"))


def _mine(user_id: uuid.UUID) -> Any:
    """Addressed to me, or a live announcement posted since my account existed."""
    joined = select(_USERS.c.created_at).where(_USERS.c.id == user_id).scalar_subquery()
    return or_(
        UserMessage.recipient_user_id == user_id,
        and_(
            UserMessage.recipient_user_id.is_(None),
            UserMessage.withdrawn_at.is_(None),
            UserMessage.created_at >= joined,
        ),
    )


async def page_for_user(
    session: AsyncSession, *, user_id: uuid.UUID, params: CursorParams
) -> tuple[list[UserMessage], str | None, set[uuid.UUID]]:
    """One page of my messages, newest first, and which of them I have read."""
    stmt = select(UserMessage).where(_mine(user_id))
    rows, next_cursor = await keyset_page(
        session,
        stmt,
        sort_col=UserMessage.created_at,
        id_col=UserMessage.id,
        limit=params.limit,
        cursor=params.cursor,
    )
    read_ids: set[uuid.UUID] = set()
    if rows:
        read_ids = set(
            (
                await session.execute(
                    select(UserMessageRead.message_id).where(
                        UserMessageRead.user_id == user_id,
                        UserMessageRead.message_id.in_([row.id for row in rows]),
                    )
                )
            ).scalars()
        )
    return rows, next_cursor, read_ids


def _unread(user_id: uuid.UUID) -> Select[Any]:
    """The ids of the messages visible to this person that they have not opened."""
    read = select(UserMessageRead.message_id).where(
        UserMessageRead.user_id == user_id, UserMessageRead.message_id == UserMessage.id
    )
    return select(UserMessage.id).where(_mine(user_id), ~read.exists())


async def unread_count(session: AsyncSession, *, user_id: uuid.UUID) -> int:
    """How many messages this person has not opened."""
    sub = _unread(user_id).subquery()
    return int((await session.execute(select(func.count()).select_from(sub))).scalar_one())


async def visible_message(
    session: AsyncSession, *, message_id: uuid.UUID, user_id: uuid.UUID
) -> UserMessage | None:
    """One message, only if it is addressed to this person or is a live announcement for them."""
    return (
        await session.execute(select(UserMessage).where(UserMessage.id == message_id, _mine(user_id)))
    ).scalar_one_or_none()


async def _insert_reads(session: AsyncSession, user_id: uuid.UUID, ids: Sequence[uuid.UUID]) -> None:
    """Write read rows, leaving any that already exist."""
    if ids:
        await session.execute(
            insert(UserMessageRead)
            .values([{"user_id": user_id, "message_id": mid} for mid in ids])
            .on_conflict_do_nothing(index_elements=["user_id", "message_id"])
        )


async def mark_read(session: AsyncSession, *, user_id: uuid.UUID, message_id: uuid.UUID) -> None:
    """Record that this person opened a message; a second time changes nothing."""
    await _insert_reads(session, user_id, [message_id])


async def mark_all_read(session: AsyncSession, *, user_id: uuid.UUID) -> None:
    """Record that this person opened everything visible to them."""
    await _insert_reads(session, user_id, list((await session.execute(_unread(user_id))).scalars()))


async def announcements_page(
    session: AsyncSession, *, params: CursorParams
) -> tuple[list[UserMessage], str | None]:
    """Every announcement, withdrawn ones included, newest first."""
    return await keyset_page(
        session,
        select(UserMessage).where(UserMessage.recipient_user_id.is_(None)),
        sort_col=UserMessage.created_at,
        id_col=UserMessage.id,
        limit=params.limit,
        cursor=params.cursor,
    )


async def read_counts(session: AsyncSession, message_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, int]:
    """How many people have opened each of these messages."""
    if not message_ids:
        return {}
    rows = await session.execute(
        select(UserMessageRead.message_id, func.count())
        .where(UserMessageRead.message_id.in_(list(message_ids)))
        .group_by(UserMessageRead.message_id)
    )
    return {message_id: count for message_id, count in rows.all()}


async def withdraw(session: AsyncSession, *, message_id: uuid.UUID, at: datetime) -> UserMessage | None:
    """Hide an announcement. `None` when there is no such announcement."""
    message = (
        await session.execute(
            select(UserMessage).where(UserMessage.id == message_id, UserMessage.recipient_user_id.is_(None))
        )
    ).scalar_one_or_none()
    if message is None:
        return None
    if message.withdrawn_at is None:
        message.withdrawn_at = at
        await session.flush()
    return message


async def delete_for_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Erase what was sent to this person. Announcements and their read rows stay."""
    await session.execute(delete(UserMessage).where(UserMessage.recipient_user_id == user_id))
