"""The marketplace "starts in an hour" reminder: who gets it, once.

Ported from legacy `b2c-api`'s `MarketplaceReminderService`. These tests call
`service_reminders.send_due_reminders` directly against a real database —
the same function `jobs.py` schedules every five minutes — and assert on
what actually reached the notifications outbox.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import PUBLIC
from app.features.identity import repository as identity_repo
from app.features.marketplace import repository, service_reminders
from app.features.notifications import repository as notifications_repo
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


async def _make_session(
    db_session: AsyncSession, *, starts_at: datetime, cancelled: bool = False
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """A scheduled peer session between two fresh accounts, starting at `starts_at`.

    Returns (peer_session_id, owner_id, claimer_id).
    """
    exam = await ensure_exam(db_session, "sca")
    owner = await identity_repo.create_user(
        db_session, email=f"owner-{uuid.uuid4().hex[:8]}@example.com", name="Owner", password_hash=None
    )
    claimer = await identity_repo.create_user(
        db_session, email=f"claimer-{uuid.uuid4().hex[:8]}@example.com", name="Claimer", password_hash=None
    )
    post = await repository.create_post(
        db_session,
        audience=PUBLIC,
        owner_user_id=owner.id,
        exam_id=exam.id,
        starts_at=starts_at,
        duration_minutes=30,
        note=None,
    )
    peer_session = await repository.create_peer_session(
        db_session,
        post_id=post.id,
        owner_user_id=owner.id,
        claimer_user_id=claimer.id,
        exam_id=exam.id,
        starts_at=starts_at,
    )
    if cancelled:
        await repository.mark_peer_cancelled(db_session, peer_session.id, at=NOW)
    await db_session.flush()
    return peer_session.id, owner.id, claimer.id


async def test_a_session_starting_within_the_hour_gets_one_email_per_participant(
    db_session: AsyncSession,
) -> None:
    """The core case: a session 45 minutes out is inside the window, and both
    the person who offered the slot and the person who claimed it are told."""
    peer_session_id, owner_id, claimer_id = await _make_session(
        db_session, starts_at=NOW + timedelta(minutes=45)
    )

    claimed = await service_reminders.send_due_reminders(db_session, now=NOW)

    assert claimed == 1
    session_row = await repository.peer_session_by_id(db_session, peer_session_id)
    assert session_row is not None
    assert session_row.reminder_sent_at == NOW

    owner_message = await notifications_repo.by_idempotency_key(
        db_session, f"marketplace-reminder-{peer_session_id}-{owner_id}"
    )
    claimer_message = await notifications_repo.by_idempotency_key(
        db_session, f"marketplace-reminder-{peer_session_id}-{claimer_id}"
    )
    assert owner_message is not None and owner_message.template_key == "marketplace_session_reminder"
    assert claimer_message is not None and claimer_message.template_key == "marketplace_session_reminder"


async def test_a_session_already_sent_its_reminder_is_never_sent_again(db_session: AsyncSession) -> None:
    """Running the job twice must not queue a second pair of emails."""
    await _make_session(db_session, starts_at=NOW + timedelta(minutes=30))

    first = await service_reminders.send_due_reminders(db_session, now=NOW)
    second = await service_reminders.send_due_reminders(db_session, now=NOW + timedelta(minutes=1))

    assert first == 1
    assert second == 0


async def test_a_session_more_than_an_hour_away_is_not_yet_due(db_session: AsyncSession) -> None:
    """Legacy sends exactly one hour before the session, not earlier."""
    peer_session_id, _, _ = await _make_session(db_session, starts_at=NOW + timedelta(minutes=90))

    claimed = await service_reminders.send_due_reminders(db_session, now=NOW)

    assert claimed == 0
    session_row = await repository.peer_session_by_id(db_session, peer_session_id)
    assert session_row is not None
    assert session_row.reminder_sent_at is None


async def test_a_session_already_past_its_start_time_is_skipped(db_session: AsyncSession) -> None:
    """A session that already started is not "due a reminder" — it is over."""
    peer_session_id, _, _ = await _make_session(db_session, starts_at=NOW - timedelta(minutes=5))

    claimed = await service_reminders.send_due_reminders(db_session, now=NOW)

    assert claimed == 0
    session_row = await repository.peer_session_by_id(db_session, peer_session_id)
    assert session_row is not None
    assert session_row.reminder_sent_at is None


async def test_a_cancelled_session_is_skipped(db_session: AsyncSession) -> None:
    """Nobody wants a reminder for a session that will not happen."""
    peer_session_id, _, _ = await _make_session(
        db_session, starts_at=NOW + timedelta(minutes=20), cancelled=True
    )

    claimed = await service_reminders.send_due_reminders(db_session, now=NOW)

    assert claimed == 0
    session_row = await repository.peer_session_by_id(db_session, peer_session_id)
    assert session_row is not None
    assert session_row.reminder_sent_at is None


async def test_a_closed_participant_is_skipped_but_the_other_still_gets_theirs(
    db_session: AsyncSession,
) -> None:
    """A closed account is not emailed; the still-active side is not silently
    left in the dark just because their partner's account is gone."""
    from app.features.identity.service_close_account import close_account

    peer_session_id, owner_id, claimer_id = await _make_session(
        db_session, starts_at=NOW + timedelta(minutes=10)
    )
    await close_account(
        db_session, user_id=owner_id, password=None, confirm="delete", now=NOW - timedelta(days=1)
    )

    claimed = await service_reminders.send_due_reminders(db_session, now=NOW)

    assert claimed == 1
    session_row = await repository.peer_session_by_id(db_session, peer_session_id)
    assert session_row is not None
    assert session_row.reminder_sent_at == NOW

    owner_message = await notifications_repo.by_idempotency_key(
        db_session, f"marketplace-reminder-{peer_session_id}-{owner_id}"
    )
    claimer_message = await notifications_repo.by_idempotency_key(
        db_session, f"marketplace-reminder-{peer_session_id}-{claimer_id}"
    )
    assert owner_message is None, "a closed account must never be queued a reminder"
    assert claimer_message is not None
