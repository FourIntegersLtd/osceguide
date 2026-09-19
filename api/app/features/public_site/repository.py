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
    row = SiteMessage(
        kind=kind,
        name=name,
        email=email,
        subject=subject,
        body=body,
        source=source,
        user_id=user_id,
    )
    session.add(row)
    await session.flush()
    return row


async def list_messages(session: AsyncSession, *, kind: str | None, limit: int) -> Sequence[SiteMessage]:
    stmt = select(SiteMessage).order_by(SiteMessage.created_at.desc()).limit(limit)
    if kind:
        stmt = stmt.where(SiteMessage.kind == kind)
    result = await session.execute(stmt)
    return result.scalars().all()


async def mark_handled(
    session: AsyncSession, *, message_id: uuid.UUID, by: uuid.UUID, at: datetime
) -> SiteMessage | None:
    row = await session.get(SiteMessage, message_id)
    if row is None:
        return None
    row.handled_at = at
    row.handled_by = by
    await session.flush()
    return row
