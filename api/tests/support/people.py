"""Accounts as the tests need them: created by `make_actor`, nudged here."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity.models import User
from app.features.notifications.models import OutboundMessage


async def mark_signed_in(db_session: AsyncSession, *, email: str) -> None:
    """Record a first sign-in, so the account no longer reads as waiting on its invitation."""
    await db_session.execute(update(User).where(User.email == email).values(last_login_at=datetime.now(UTC)))


async def invitations_to(db_session: AsyncSession, recipient: str) -> list[OutboundMessage]:
    """The invitation emails queued for this address, oldest first."""
    stmt = (
        select(OutboundMessage)
        .where(OutboundMessage.template_key == "invitation", OutboundMessage.recipient == recipient)
        .order_by(OutboundMessage.available_at)
    )
    return list((await db_session.execute(stmt)).scalars())
