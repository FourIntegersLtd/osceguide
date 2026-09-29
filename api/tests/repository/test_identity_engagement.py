"""The "come try a station" nudge for someone who signed up and never practised.

Ported from legacy `b2c-api`'s `InactiveUserEngagementService`. These tests
call `service_engagement.send_due_engagement_emails` directly against a real
database — the same function `jobs.py` schedules once a day — and assert on
what actually reached the notifications outbox.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import repository as attempts_repo
from app.features.identity import repository as identity_repo
from app.features.identity.models import User
from app.features.identity.service_close_account import close_account
from app.features.identity.service_engagement import LOOKBACK_DAYS, send_due_engagement_emails
from app.features.notifications import repository as notifications_repo
from app.features.roster import repository as roster_repo
from app.features.tenancy import repository as tenancy_repo
from tests.support.catalog import ensure_exam
from tests.support.finished_consultation import finish_consultation

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


async def _create_user_signed_up(db_session: AsyncSession, *, created_at: datetime) -> uuid.UUID:
    """A fresh account, backdated to `created_at`.

    `identity_repo.create_user` always stamps `created_at` at the moment of
    the call (the column's server default), so the window this job cares
    about has to be set afterwards, the way an imported account's real
    sign-up date is set by `app.migration` rather than by `INSERT`'s own
    default.
    """
    user = await identity_repo.create_user(
        db_session, email=f"u-{uuid.uuid4().hex[:8]}@example.com", name="Candidate", password_hash=None
    )
    await db_session.execute(update(User).where(User.id == user.id).values(created_at=created_at))
    await db_session.flush()
    return user.id


def _outbox_key(user_id: uuid.UUID) -> str:
    return f"inactive-engagement-{user_id}"


async def test_a_recent_signup_who_never_practised_is_emailed(db_session: AsyncSession) -> None:
    """The core case: signed up 10 days ago, inside the 28-day window, and has
    never finished a station."""
    user_id = await _create_user_signed_up(db_session, created_at=NOW - timedelta(days=10))

    sent = await send_due_engagement_emails(db_session, now=NOW)

    assert sent == 1
    user = await identity_repo.user_by_id(db_session, user_id)
    assert user is not None
    assert user.engagement_email_sent_at == NOW
    message = await notifications_repo.by_idempotency_key(db_session, _outbox_key(user_id))
    assert message is not None
    assert message.template_key == "inactive_user_engagement"


async def test_running_the_job_twice_sends_only_once(db_session: AsyncSession) -> None:
    """A second run of the same day, or an overlapping worker, must not
    re-queue the email."""
    await _create_user_signed_up(db_session, created_at=NOW - timedelta(days=5))

    first = await send_due_engagement_emails(db_session, now=NOW)
    second = await send_due_engagement_emails(db_session, now=NOW + timedelta(minutes=1))

    assert first == 1
    assert second == 0


async def test_a_signup_outside_the_lookback_window_is_not_emailed(db_session: AsyncSession) -> None:
    """Legacy's own number: 28 days. One day past it is too old for the nudge."""
    user_id = await _create_user_signed_up(db_session, created_at=NOW - timedelta(days=LOOKBACK_DAYS + 1))

    sent = await send_due_engagement_emails(db_session, now=NOW)

    assert sent == 0
    user = await identity_repo.user_by_id(db_session, user_id)
    assert user is not None
    assert user.engagement_email_sent_at is None


async def test_someone_who_already_completed_a_station_is_not_emailed(db_session: AsyncSession) -> None:
    """legacy's `user_has_completed_station` check: no nudge once they have
    actually tried one."""
    user_id = await _create_user_signed_up(db_session, created_at=NOW - timedelta(days=3))
    exam = await ensure_exam(db_session, "sca")
    attempt = await attempts_repo.create_attempt(
        db_session, kind="practice", user_id=user_id, exam_id=exam.id
    )
    await finish_consultation(db_session, attempt.id)

    sent = await send_due_engagement_emails(db_session, now=NOW)

    assert sent == 0
    user = await identity_repo.user_by_id(db_session, user_id)
    assert user is not None
    assert user.engagement_email_sent_at is None


async def test_an_institution_trainee_is_never_emailed(db_session: AsyncSession) -> None:
    """New to this port: legacy's Firestore users were consumer accounts by
    construction, but the unified `users` table also holds institution
    trainees. A person who exists here only as a roster entry must not get
    a consumer engagement nudge."""
    user_id = await _create_user_signed_up(db_session, created_at=NOW - timedelta(days=2))
    org = await tenancy_repo.create_organization(db_session, slug=f"org-{uuid.uuid4().hex[:8]}", name="Org")
    trainee = await roster_repo.create_trainee(
        db_session,
        org.id,
        email=f"t-{uuid.uuid4().hex[:8]}@example.com",
        first_name=None,
        last_name=None,
        cohort_id=None,
    )
    await roster_repo.link_trainee_to_user(db_session, org.id, trainee.id, user_id=user_id)

    sent = await send_due_engagement_emails(db_session, now=NOW)

    assert sent == 0
    user = await identity_repo.user_by_id(db_session, user_id)
    assert user is not None
    assert user.engagement_email_sent_at is None


async def test_a_closed_account_is_never_emailed(db_session: AsyncSession) -> None:
    """legacy's `_should_send_engagement_email` refuses a deleted account."""
    user_id = await _create_user_signed_up(db_session, created_at=NOW - timedelta(days=4))
    await close_account(
        db_session, user_id=user_id, password=None, confirm="delete", now=NOW - timedelta(days=1)
    )

    sent = await send_due_engagement_emails(db_session, now=NOW)

    assert sent == 0


async def test_someone_already_sent_the_email_before_is_skipped(db_session: AsyncSession) -> None:
    """The idempotency column itself, set as if by an earlier run (or, in
    production, backfilled from legacy's `inactive_engagement_email_sent_at`
    by `app.migration`)."""
    user_id = await _create_user_signed_up(db_session, created_at=NOW - timedelta(days=6))
    await db_session.execute(
        update(User).where(User.id == user_id).values(engagement_email_sent_at=NOW - timedelta(days=1))
    )
    await db_session.flush()

    sent = await send_due_engagement_emails(db_session, now=NOW)

    assert sent == 0
