"""Sending a person a message inside the app, and showing them what they have.

`deliver` is the single write path: every kind of message goes through it, so each one
is audited and each one wakes the recipient's open tabs.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.events import publish_after_commit, user_topic
from app.core.pagination import CursorParams, Page
from app.features.identity import service as identity
from app.features.inbox import domain, errors, repository, schemas
from app.features.inbox.models import UserMessage
from app.features.tenancy import service_audit


async def deliver(
    session: AsyncSession,
    *,
    actor: Principal,
    recipient_id: uuid.UUID | None,
    kind: domain.Kind,
    subject: str,
    body: str,
    station_flag_id: uuid.UUID | None = None,
    site_message_id: uuid.UUID | None = None,
) -> UserMessage:
    """Write one message (no recipient means an announcement) and audit it.

    A message to a person also wakes their open tabs after the commit. An announcement has
    no topic to publish to: open tabs find it on resync or navigation.
    """
    message = await repository.add_message(
        session,
        recipient_user_id=recipient_id,
        sender_user_id=actor.user_id,
        kind=kind,
        subject=subject,
        body=body,
        station_flag_id=station_flag_id,
        site_message_id=site_message_id,
    )
    await service_audit.record(
        session,
        actor=actor,
        action=f"inbox.{kind}_sent" if recipient_id else "inbox.announcement_posted",
        target_type="user" if recipient_id else "announcement",
        target_id=str(recipient_id or message.id),
        summary=subject,
        meta={"message_id": str(message.id)},
    )
    if recipient_id:
        publish_after_commit(
            session, user_topic(recipient_id), "message.received", {"message_id": str(message.id)}
        )
    return message


# The wrappers below are the boundary: the slice guard stops stations and public_site importing
# `inbox.domain`, so the wording of each message is decided here.
async def deliver_report_answer(
    session: AsyncSession,
    *,
    actor: Principal,
    flag_id: uuid.UUID,
    recipient_id: uuid.UUID,
    station_title: str | None,
    note: str | None,
) -> UserMessage:
    """Tell a reporter their station report was closed, in words that name the station."""
    return await deliver(
        session,
        actor=actor,
        recipient_id=recipient_id,
        kind="report_answer",
        subject=domain.report_answer_subject(station_title),
        body=domain.report_answer_body(note),
        station_flag_id=flag_id,
    )


async def deliver_reply(
    session: AsyncSession,
    *,
    actor: Principal,
    site_message_id: uuid.UUID,
    recipient_id: uuid.UUID,
    original_subject: str | None,
    body: str,
) -> UserMessage:
    """Answer a message somebody sent us from inside the product."""
    return await deliver(
        session,
        actor=actor,
        recipient_id=recipient_id,
        kind="reply",
        subject=domain.reply_subject(original_subject),
        body=body.strip(),
        site_message_id=site_message_id,
    )


async def send_note(
    session: AsyncSession, *, actor: Principal, user_id: uuid.UUID, body: schemas.SendUserNote
) -> schemas.SentInboxMessage:
    """Send a staff note to one person, refusing an unknown user."""
    if await identity.user_ref_by_id(session, user_id) is None:
        raise errors.UserNotFound()
    message = await deliver(
        session,
        actor=actor,
        recipient_id=user_id,
        kind="note",
        subject=body.subject.strip(),
        body=body.body.strip(),
    )
    return _sent(message)


async def post_announcement(
    session: AsyncSession, *, actor: Principal, body: schemas.PostAnnouncement
) -> schemas.SentInboxMessage:
    """Post a message every existing account will see."""
    message = await deliver(
        session,
        actor=actor,
        recipient_id=None,
        kind="announcement",
        subject=body.subject.strip(),
        body=body.body.strip(),
    )
    return _sent(message)


async def list_announcements(
    session: AsyncSession, *, params: CursorParams
) -> Page[schemas.PlatformAnnouncementRead]:
    """The announcements staff have posted, with read counts and who posted them."""
    rows, next_cursor = await repository.announcements_page(session, params=params)
    return Page(items=await _announcements_view(session, rows), next_cursor=next_cursor)


async def withdraw_announcement(
    session: AsyncSession, *, actor: Principal, message_id: uuid.UUID, at: datetime
) -> schemas.PlatformAnnouncementRead:
    """Hide an announcement from every inbox and record who did it."""
    message = await repository.withdraw(session, message_id=message_id, at=at)
    if message is None:
        raise errors.AnnouncementNotFound()
    await service_audit.record(
        session,
        actor=actor,
        action="inbox.announcement_withdrawn",
        target_type="announcement",
        target_id=str(message_id),
        summary=message.subject,
    )
    return (await _announcements_view(session, [message]))[0]


async def _announcements_view(
    session: AsyncSession, rows: Sequence[UserMessage]
) -> list[schemas.PlatformAnnouncementRead]:
    """Announcements as staff see them, with read counts and sender names looked up once."""
    counts = await repository.read_counts(session, [row.id for row in rows])
    senders = await identity.user_refs_by_ids(
        session, list({row.sender_user_id for row in rows if row.sender_user_id})
    )
    return [
        schemas.PlatformAnnouncementRead.model_validate(
            {
                **{
                    field: getattr(row, field)
                    for field in ("id", "subject", "body", "created_at", "withdrawn_at")
                },
                "read_count": counts.get(row.id, 0),
                "sender_name": senders[row.sender_user_id].name if row.sender_user_id in senders else None,
            }
        )
        for row in rows
    ]


async def my_messages(
    session: AsyncSession, *, user_id: uuid.UUID, params: CursorParams
) -> Page[schemas.InboxMessageRead]:
    """One page of the inbox, newest first."""
    rows, next_cursor, read_ids = await repository.page_for_user(session, user_id=user_id, params=params)
    return Page(
        items=[
            schemas.InboxMessageRead.model_validate(
                {
                    **{
                        field: getattr(row, field)
                        for field in ("id", "kind", "subject", "body", "created_at")
                    },
                    "from_label": domain.FROM_LABEL,
                    "read": row.id in read_ids,
                }
            )
            for row in rows
        ],
        next_cursor=next_cursor,
    )


async def unread_count(session: AsyncSession, *, user_id: uuid.UUID) -> schemas.InboxUnreadCount:
    """How many messages this person has not opened."""
    return schemas.InboxUnreadCount(count=await repository.unread_count(session, user_id=user_id))


async def mark_read(session: AsyncSession, *, user_id: uuid.UUID, message_id: uuid.UUID) -> None:
    """Mark one message as read, refusing one the person cannot see."""
    if await repository.visible_message(session, message_id=message_id, user_id=user_id) is None:
        raise errors.InboxMessageNotFound()
    await repository.mark_read(session, user_id=user_id, message_id=message_id)


async def mark_all_read(session: AsyncSession, *, user_id: uuid.UUID) -> None:
    """Mark everything this person can see as read."""
    await repository.mark_all_read(session, user_id=user_id)


async def erase_for_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Delete everything sent to this person, for account erasure."""
    await repository.delete_for_user(session, user_id)


def _sent(message: UserMessage) -> schemas.SentInboxMessage:
    """A stored message as the staff member who sent it sees it."""
    return schemas.SentInboxMessage.model_validate(message, from_attributes=True)
