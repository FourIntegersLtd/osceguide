"""An imported subscriber must be capped to their plan, which needs the payment tied to the grant."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import repository as billing_repo
from app.features.billing import service_station_limit
from app.features.billing.models import Payment
from app.features.entitlements.models import Entitlement
from app.migration import loader
from app.migration.link_payments import link_legacy_payments
from app.migration.load_legacy_b2c import load_legacy_payments
from app.migration.users import entitlements_for, legacy_payment_for, merge_users
from tests.migration.test_loader import b2c_transcript, b2c_user
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db

NOW = datetime(2026, 10, 20, tzinfo=UTC)


async def _import_buyer(session: AsyncSession, *, intent: str | None) -> tuple[object, dict]:
    """One paid SCA user with a 30 day plan imported through the real loaders."""
    exam = await ensure_exam(session, "sca")
    await billing_repo.create_plan(
        session,
        code="sca_1m",
        stripe_price_id="price_sca_1m",
        amount_pence=2499,
        duration_days=30,
        exam_code="sca",
        station_limit=53,
    )
    record = b2c_user(
        "buyer@example.com",
        "sca",
        "fs-buyer",
        has_paid=True,
        plan_type="one_month",
        plan_start_date="2026-10-06T10:00:00Z",
        plan_end_date="2026-11-05T10:00:00Z",
        stripe_payment_intent_id=intent or "",
    )
    merged = merge_users([record])
    _, ids, email_ids = await loader.load_users(session, merged, entitlements_for(record))
    payment = legacy_payment_for(record)
    assert payment is not None
    await load_legacy_payments(session, [payment], user_ids=email_ids)
    return exam, {"user_id": email_ids["buyer@example.com"]}


async def test_an_imported_buyer_is_capped_to_the_plan_limit(db_session: AsyncSession) -> None:
    exam, found = await _import_buyer(db_session, intent="pi_real_1")

    limit = await service_station_limit.station_limit_for(
        db_session, user_id=found["user_id"], exam_id=exam.id, exam_code="sca", now=NOW
    )

    assert limit == 53


async def test_linking_twice_changes_nothing_the_second_time(db_session: AsyncSession) -> None:
    _, found = await _import_buyer(db_session, intent="pi_real_2")

    second = await link_legacy_payments(db_session, user_ids={found["user_id"]})

    assert second.linked == 0
    payment = await db_session.scalar(select(Payment).where(Payment.stripe_payment_intent_id == "pi_real_2"))
    assert payment is not None and payment.entitlement_id is not None


def test_a_grant_with_no_end_date_is_dated_from_its_plan_length() -> None:
    record = b2c_user(
        "open@example.com",
        "sca",
        "fs-open",
        has_paid=True,
        plan_type="three_month",
        plan_start_date="2026-01-10T00:00:00Z",
    )

    (grant,) = entitlements_for(record)

    assert grant.ends_at == datetime(2026, 4, 10, tzinfo=UTC)


def test_a_grant_with_no_start_date_is_dated_back_from_its_end() -> None:
    record = b2c_user(
        "nostart@example.com",
        "sca",
        "fs-nostart",
        has_paid=True,
        plan_type="one_month",
        plan_end_date="2026-06-11T00:00:00Z",
    )

    (grant,) = entitlements_for(record)

    assert grant.starts_at == datetime(2026, 5, 12, tzinfo=UTC)


async def test_an_imported_user_trial_starts_at_their_legacy_signup(
    db_session: AsyncSession,
) -> None:
    from app.features.identity.models import User

    record = b2c_user("old@example.com", "sca", "fs-old", created_at="2025-01-15T09:00:00Z")
    await loader.load_users(db_session, merge_users([record]))

    user = await db_session.scalar(select(User).where(User.email == "old@example.com"))

    assert user is not None
    assert user.activated_at == datetime(2025, 1, 15, 9, 0, tzinfo=UTC)


def test_two_attempts_at_one_station_keep_their_own_marks() -> None:
    from app.migration.b2c_lookups import StepReport
    from app.migration.load_b2c_attempts import migrate_transcripts

    def transcript(attempt_id: str, at: str) -> dict:
        return {
            **b2c_transcript("fs-1", f"t-{attempt_id}", turns=2),
            "attempt_id": attempt_id,
            "app_type": "sca",
            "created_at": at,
        }

    first, retry = transcript("a-1", "2026-02-01T10:00:00Z"), transcript("a-2", "2026-03-01T10:00:00Z")
    feedback = {
        "attempt_id": "a-1",
        "app_type": "sca",
        "user_id": "fs-1",
        "mock_id": "m-1",
        "station_id": "s-1",
    }

    pairs = migrate_transcripts([first, retry], [feedback], StepReport())

    marked = {raw["attempt_id"]: migrated.result is not None for migrated, raw in pairs}
    assert marked == {"a-1": True, "a-2": False}


def test_feedback_with_a_placeholder_attempt_id_still_marks_its_transcript() -> None:
    from app.migration.b2c_lookups import StepReport
    from app.migration.load_b2c_attempts import migrate_transcripts

    transcript = {
        **b2c_transcript("fs-1", "t-1", turns=2),
        "attempt_id": "a-real",
        "app_type": "sca",
        "mock_id": "m-1",
        "station_id": "s-1",
    }
    feedback = {
        "attempt_id": "attempt-789",
        "app_type": "sca",
        "user_id": "fs-1",
        "mock_id": "m-1",
        "station_id": "s-1",
    }

    pairs = migrate_transcripts([transcript], [feedback], StepReport())

    assert [migrated.result is not None for migrated, _ in pairs] == [True]


async def _import_with_end(session: AsyncSession, plan_end: str):  # type: ignore[no-untyped-def]
    """Load the same paid user with the given legacy plan end date; returns the load report."""
    record = b2c_user(
        "renewer@example.com",
        "sca",
        "fs-renewer",
        has_paid=True,
        plan_type="one_month",
        plan_start_date="2026-10-06T10:00:00Z",
        plan_end_date=plan_end,
    )
    report, _, _ = await loader.load_users(session, merge_users([record]), entitlements_for(record))
    return report


async def _grant_end(session: AsyncSession) -> str:
    """The stored end date of the one imported grant, as YYYY-MM-DD."""
    ends_at = await session.scalar(
        select(Entitlement.ends_at).where(Entitlement.source_ref == "legacy-import")
    )
    return ends_at.date().isoformat()


async def test_a_renewal_in_the_old_app_extends_the_grant_on_re_import(db_session: AsyncSession) -> None:
    """Importing again after a renewal moves the end date later, and never earlier."""
    await ensure_exam(db_session, "sca")
    await _import_with_end(db_session, "2026-11-05T10:00:00Z")

    report = await _import_with_end(db_session, "2026-12-05T10:00:00Z")
    assert report.entitlements_extended == 1
    assert await _grant_end(db_session) == "2026-12-05"

    await _import_with_end(db_session, "2026-11-20T10:00:00Z")
    assert await _grant_end(db_session) == "2026-12-05"
