"""What the database guarantees about in-app messages."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorParams
from app.features.identity import repository as identity_repo
from app.features.identity.models import User
from app.features.inbox import repository
from app.features.inbox.models import UserMessage

pytestmark = pytest.mark.db

LONG_AGO = datetime(2026, 1, 1, tzinfo=UTC)
JOINED = datetime(2026, 6, 1, tzinfo=UTC)


async def a_user(session: AsyncSession, email: str = "reader@example.com"):  # type: ignore[no-untyped-def]
    user = await identity_repo.create_user(session, email=email, name="Reader", password_hash=None)
    # Every row in a test shares one transaction timestamp, so say when the account was made.
    await session.execute(update(User).where(User.id == user.id).values(created_at=JOINED))
    return user


async def note(session: AsyncSession, to: uuid.UUID | None, kind: str = "note", at: datetime | None = None):  # type: ignore[no-untyped-def]
    message = await repository.add_message(
        session, recipient_user_id=to, sender_user_id=None, kind=kind, subject="S", body="B"
    )
    if at is not None:
        await session.execute(update(UserMessage).where(UserMessage.id == message.id).values(created_at=at))
        await session.refresh(message)
    return message


async def test_an_announcement_with_a_recipient_is_refused(db_session: AsyncSession) -> None:
    user = await a_user(db_session)
    with pytest.raises(IntegrityError):
        await note(db_session, user.id, kind="announcement")


async def test_a_note_without_a_recipient_is_refused(db_session: AsyncSession) -> None:
    with pytest.raises(IntegrityError):
        await note(db_session, None, kind="note")


async def test_an_announcement_from_before_the_account_is_invisible(db_session: AsyncSession) -> None:
    user = await a_user(db_session)
    await note(db_session, None, kind="announcement", at=JOINED - timedelta(days=1))
    fresh = await note(db_session, None, kind="announcement", at=JOINED + timedelta(days=1))
    rows, _, _ = await repository.page_for_user(db_session, user_id=user.id, params=CursorParams(limit=10))
    assert [row.id for row in rows] == [fresh.id]


async def test_unread_count_covers_my_messages_and_live_announcements_only(db_session: AsyncSession) -> None:
    me = await a_user(db_session)
    other = await a_user(db_session, "other@example.com")
    mine = await note(db_session, me.id)
    await note(db_session, other.id)
    await note(db_session, None, kind="announcement", at=JOINED + timedelta(days=1))
    gone = await note(db_session, None, kind="announcement", at=JOINED + timedelta(days=2))
    await repository.withdraw(db_session, message_id=gone.id, at=JOINED + timedelta(days=3))

    assert await repository.unread_count(db_session, user_id=me.id) == 2
    await repository.mark_read(db_session, user_id=me.id, message_id=mine.id)
    assert await repository.unread_count(db_session, user_id=me.id) == 1
    await repository.mark_all_read(db_session, user_id=me.id)
    assert await repository.unread_count(db_session, user_id=me.id) == 0


async def test_reading_twice_is_harmless(db_session: AsyncSession) -> None:
    me = await a_user(db_session)
    message = await note(db_session, me.id)
    await repository.mark_read(db_session, user_id=me.id, message_id=message.id)
    await repository.mark_read(db_session, user_id=me.id, message_id=message.id)
    assert await repository.read_counts(db_session, [message.id]) == {message.id: 1}


async def test_messages_sharing_a_timestamp_page_without_repeats(db_session: AsyncSession) -> None:
    me = await a_user(db_session)
    ids = {(await note(db_session, me.id)).id for _ in range(5)}
    first, cursor, _ = await repository.page_for_user(db_session, user_id=me.id, params=CursorParams(limit=2))
    seen = [row.id for row in first]
    while cursor:
        page = CursorParams(cursor=cursor, limit=2)
        rows, cursor, _ = await repository.page_for_user(db_session, user_id=me.id, params=page)
        seen += [row.id for row in rows]
    assert len(seen) == 5 and set(seen) == ids


async def test_erasing_an_account_removes_its_messages_but_not_announcements(
    db_session: AsyncSession,
) -> None:
    from app.features.inbox import service

    me = await a_user(db_session)
    await note(db_session, me.id)
    announcement = await note(db_session, None, kind="announcement")
    await service.erase_for_user(db_session, me.id)
    rows, _, _ = await repository.page_for_user(db_session, user_id=me.id, params=CursorParams(limit=10))
    assert [row.id for row in rows] == [announcement.id]


async def test_delivering_stores_the_row_audits_it_and_queues_the_event(db_session: AsyncSession) -> None:
    from sqlalchemy import select

    from app.core.auth import Principal
    from app.core.events import PENDING_KEY, user_topic
    from app.features.inbox import service
    from app.features.tenancy.models import AuditEntry

    staff = await a_user(db_session, "staff@example.com")
    me = await a_user(db_session)
    actor = Principal(user_id=staff.id, email=staff.email, is_platform_admin=True)

    sent = await service.deliver(
        db_session, actor=actor, recipient_id=me.id, kind="note", subject="Hello", body="There"
    )

    stored = await db_session.get(UserMessage, sent.id)
    assert stored is not None and (stored.recipient_user_id, stored.subject) == (me.id, "Hello")
    audit = (
        await db_session.execute(select(AuditEntry.action).where(AuditEntry.target_id == str(me.id)))
    ).scalars()
    assert list(audit) == ["inbox.note_sent"]
    assert db_session.info[PENDING_KEY] == [
        (user_topic(me.id), "message.received", {"message_id": str(sent.id)})
    ]
