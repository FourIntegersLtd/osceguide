"""Storage for messages sent through the public site's contact form and in-product feedback box."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.public_site.models import SiteMessage


async def add_message(
    session: AsyncSession,
    *,
    kind: str,
    name: str | None,
    email: str | None,
    subject: str | None,
    body: str,
    source: str | None,
    user_id: uuid.UUID | None,
) -> SiteMessage:
    """Store one message sent through the contact form or the in-product feedback box."""
    message = SiteMessage(
        kind=kind,
        name=name,
        email=email,
        subject=subject,
        body=body,
        source=source,
        user_id=user_id,
    )
    session.add(message)
    await session.flush()
    return message


async def list_messages(session: AsyncSession, *, kind: str | None, limit: int) -> Sequence[SiteMessage]:
    """Every message, newest first, optionally narrowed to one kind."""
    stmt = select(SiteMessage).order_by(SiteMessage.created_at.desc()).limit(limit)
    if kind:
        stmt = stmt.where(SiteMessage.kind == kind)
    found = await session.execute(stmt)
    return found.scalars().all()


async def mark_handled(
    session: AsyncSession, *, message_id: uuid.UUID, by: uuid.UUID, at: datetime
) -> SiteMessage | None:
    """Mark one message as dealt with, or `None` if no message has that id."""
    message = await session.get(SiteMessage, message_id)
    if message is None:
        return None
    message.handled_at = at
    message.handled_by = by
    await session.flush()
    return message
