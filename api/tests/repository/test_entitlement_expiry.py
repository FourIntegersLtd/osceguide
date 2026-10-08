"""The week-before warning that paid access is about to end (S-12, E-1)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.entitlements import repository as ent_repo
from app.features.entitlements.service_expiry import WARN_DAYS, warn_expiring_access
from app.features.identity import repository as identity_repo
from app.features.notifications import repository as notifications_repo
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)


async def _holder(db_session: AsyncSession, *, source: str, ends_in: timedelta, revoked: bool = False):
    user = await identity_repo.create_user(
        db_session, email=f"p-{uuid.uuid4().hex[:8]}@example.com", name="Payer", password_hash=None
    )
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    grant = await ent_repo.grant(
        db_session, user_id=user.id, exam_id=exam.id, source=source, ends_at=NOW + ends_in
    )
    if revoked:
        await ent_repo.revoke(db_session, grant.id, at=NOW)
    await db_session.flush()
    return user, grant


async def test_a_purchase_ending_within_the_week_is_warned_once(db_session: AsyncSession) -> None:
    user, grant = await _holder(db_session, source="purchase", ends_in=timedelta(days=3))

    first = await warn_expiring_access(db_session, now=NOW)
    second = await warn_expiring_access(db_session, now=NOW + timedelta(hours=1))

    assert (first, second) == (1, 0)
    message = await notifications_repo.by_idempotency_key(db_session, f"entitlement_expiring:{grant.id}")
    assert message is not None
    assert message.recipient == user.email
    assert message.template_key == "entitlement_expiring"


async def test_access_ending_later_or_not_bought_is_not_warned(db_session: AsyncSession) -> None:
    await _holder(db_session, source="purchase", ends_in=timedelta(days=WARN_DAYS + 5))
    await _holder(db_session, source="org_grant", ends_in=timedelta(days=2))
    await _holder(db_session, source="purchase", ends_in=timedelta(days=2), revoked=True)
    await _holder(db_session, source="purchase", ends_in=-timedelta(days=1))

    assert await warn_expiring_access(db_session, now=NOW) == 0


async def test_other_access_that_outlasts_it_stops_the_warning(db_session: AsyncSession) -> None:
    """Any live source counts, and open-ended access (no end date) outlasts everything."""
    user, _ = await _holder(db_session, source="purchase", ends_in=timedelta(days=3))
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    await ent_repo.grant(db_session, user_id=user.id, exam_id=exam.id, source="admin", ends_at=None)
    await db_session.flush()

    assert await warn_expiring_access(db_session, now=NOW) == 0


async def test_a_plan_no_longer_than_the_warning_is_not_warned(db_session: AsyncSession) -> None:
    user = await identity_repo.create_user(
        db_session, email="short@example.com", name="Payer", password_hash=None
    )
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    await ent_repo.grant(
        db_session,
        user_id=user.id,
        exam_id=exam.id,
        source="purchase",
        starts_at=NOW - timedelta(hours=1),
        ends_at=NOW + timedelta(days=WARN_DAYS) - timedelta(hours=1),
    )
    await db_session.flush()

    assert await warn_expiring_access(db_session, now=NOW) == 0
