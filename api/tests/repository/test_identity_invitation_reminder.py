"""E-5: an invitation nobody has answered is reminded once, on day five.

Calls `send_due_invitation_reminders` (what the daily job runs) against a real database and
reads the outbox, which is where a reminder actually lands.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import repository as identity_repo
from app.features.identity.service_invitations import invite_user, send_due_invitation_reminders
from app.features.identity.tokens import _hash_sync
from app.features.notifications.models import OutboundMessage

pytestmark = pytest.mark.db

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


async def reminders(db_session: AsyncSession) -> list[OutboundMessage]:
    stmt = select(OutboundMessage).where(OutboundMessage.template_key == "invitation_reminder")
    return list((await db_session.execute(stmt)).scalars())


async def test_an_invitation_unanswered_for_five_days_is_reminded_once_with_a_fresh_link(
    db_session: AsyncSession,
) -> None:
    await invite_user(db_session, email="wait@example.com", name="Wait", invited_to="Acme", now=NOW)

    sent = [
        await send_due_invitation_reminders(db_session, now=NOW + timedelta(days=day)) for day in (4, 5, 6)
    ]

    assert sent == [0, 1, 0]
    [reminder] = await reminders(db_session)
    assert reminder.recipient == "wait@example.com"
    assert reminder.payload is not None
    assert reminder.payload["invited_to"] == "Acme"
    assert reminder.payload["token"]


async def test_an_invitation_already_answered_or_expired_is_not_reminded(db_session: AsyncSession) -> None:
    answered = await invite_user(
        db_session, email="done@example.com", name="Done", invited_to="Acme", now=NOW
    )
    await identity_repo.set_password_hash(db_session, answered.id, _hash_sync("a long enough passphrase"))
    await invite_user(db_session, email="late@example.com", name="Late", invited_to="Acme", now=NOW)

    # Day 5 reaches only the pending one; by day 8 the link has expired and a person must re-invite.
    assert await send_due_invitation_reminders(db_session, now=NOW + timedelta(days=5)) == 1
    assert await send_due_invitation_reminders(db_session, now=NOW + timedelta(days=9)) == 0
    assert [m.recipient for m in await reminders(db_session)] == ["late@example.com"]
