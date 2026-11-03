"""What billing-access says about each exam, and that a free grant is not counted as a sale."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import repository as billing_repo
from app.features.billing import service as billing_service
from app.features.catalog.models import Exam
from app.features.entitlements import repository as ent_repo
from app.features.identity import repository as identity_repo
from app.features.notifications.models import OutboundMessage
from tests.http.test_billing_routes import a_customer, checkout_event, post_event
from tests.support.billing import a_plan
from tests.support.catalog import ensure_exam
from tests.support.sittings import org_with_admin
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def a_buyer(db_session: AsyncSession, email: str) -> uuid.UUID:
    """A registered account, read back as a plain id."""
    await a_customer(db_session, email)
    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    return user.id


async def a_sca_plan(db_session: AsyncSession, code: str, days: int, limit: int | None) -> None:
    """A plan on the `sca` exam with this length and station limit."""
    await ensure_exam(db_session, "sca")
    await billing_repo.create_plan(
        db_session,
        code=code,
        stripe_price_id=f"price_{code}",
        amount_pence=1000,
        duration_days=days,
        exam_code="sca",
        station_limit=limit,
    )
    await db_session.flush()


async def buy(client: AsyncClient, root: str, user_id: uuid.UUID, plan_code: str, **extra) -> dict:  # type: ignore[no-untyped-def,type-arg]
    """Record a manual purchase of a plan and return the payment."""
    response = await client.post(
        f"/api/v1/platform/users/{user_id}/payments",
        json={"plan_code": plan_code, "note": "test", **extra},
        headers=bearer(root),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def access_rows(client: AsyncClient, root: str, user_id: uuid.UUID) -> dict[str, dict]:  # type: ignore[type-arg]
    """The billing-access rows keyed by exam code."""
    response = await client.get(f"/api/v1/platform/users/{user_id}/billing-access", headers=bearer(root))
    assert response.status_code == 200, response.text
    return {row["exam_code"]: row for row in response.json()["items"]}


async def test_a_retired_or_institution_exam_does_not_break_the_read(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    org_id, _ = await org_with_admin(client, make_actor)
    retired = await ensure_exam(db_session, "plab")
    owned = await ensure_exam(db_session, "casc")
    owned_id, retired_id = owned.id, retired.id
    await db_session.execute(update(Exam).where(Exam.id == retired_id).values(status="retired"))
    await db_session.execute(update(Exam).where(Exam.id == owned_id).values(owner_kind="org", org_id=org_id))
    user_id = await a_buyer(db_session, "mixed@example.com")
    await ent_repo.grant(db_session, user_id=user_id, exam_id=owned_id, source="org_grant")
    await ent_repo.grant(db_session, user_id=user_id, exam_id=retired_id, source="org_grant")
    await db_session.flush()

    rows = await access_rows(client, root, user_id)
    assert sorted(rows) == ["casc", "plab"]
    assert rows["casc"]["limit_reason"] == "unlimited:org_grant"
    assert rows["plab"]["station_limit"] is None


async def test_the_reason_names_the_running_plan_and_ignores_one_not_started(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_sca_plan(db_session, "sca_6m", 180, 100)
    await a_sca_plan(db_session, "sca_1m", 30, 40)
    user_id = await a_buyer(db_session, "stacked@example.com")
    await buy(client, root, user_id, "sca_6m")
    await buy(client, root, user_id, "sca_1m")

    row = (await access_rows(client, root, user_id))["sca"]
    assert (row["limit_reason"], row["station_limit"]) == ("plan:sca_6m", 100)
    assert [grant["plan_code"] for grant in row["grants"]].count("sca_1m") == 1


async def test_only_a_queued_purchase_is_no_access(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_sca_plan(db_session, "sca_1m", 30, 40)
    user_id = await a_buyer(db_session, "queued@example.com")
    bought = await buy(client, root, user_id, "sca_1m")
    later = datetime.now(UTC) + timedelta(days=10)
    await db_session.execute(
        update(ent_repo.Entitlement)
        .where(ent_repo.Entitlement.id == uuid.UUID(bought["entitlement_id"]))
        .values(starts_at=later, ends_at=later + timedelta(days=30))
    )
    await db_session.flush()

    row = (await access_rows(client, root, user_id))["sca"]
    assert row["limit_reason"] == "no_access"
    assert row["grants"][0]["live"] is False


async def test_a_revoked_or_lapsed_grant_is_no_access_and_shows_when_it_was_revoked(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_sca_plan(db_session, "sca_1m", 30, 40)
    revoked_user = await a_buyer(db_session, "revoked@example.com")
    lapsed_user = await a_buyer(db_session, "lapsed@example.com")
    revoked = await buy(client, root, revoked_user, "sca_1m")
    lapsed = await buy(client, root, lapsed_user, "sca_1m")
    assert (
        await client.post(
            f"/api/v1/platform/entitlements/{revoked['entitlement_id']}/revoke",
            json={"reason": "refunded"},
            headers=bearer(root),
        )
    ).status_code == 200
    await ent_repo.set_ends_at(
        db_session, uuid.UUID(lapsed["entitlement_id"]), ends_at=datetime.now(UTC) - timedelta(days=1)
    )
    await db_session.flush()

    revoked_row = (await access_rows(client, root, revoked_user))["sca"]
    assert revoked_row["limit_reason"] == "no_access"
    assert revoked_row["grants"][0]["revoked_at"] is not None
    assert (await access_rows(client, root, lapsed_user))["sca"]["limit_reason"] == "no_access"


async def test_an_uncapped_plan_has_no_limit_but_still_names_the_plan(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_sca_plan(db_session, "sca_all", 30, None)
    user_id = await a_buyer(db_session, "uncapped@example.com")
    await buy(client, root, user_id, "sca_all")

    row = (await access_rows(client, root, user_id))["sca"]
    assert (row["limit_reason"], row["station_limit"]) == ("plan:sca_all", None)


async def test_a_bought_grant_carries_its_payment_and_an_unbought_one_carries_none(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_sca_plan(db_session, "sca_1m", 30, 40)
    exam = await ensure_exam(db_session, "sca")
    user_id = await a_buyer(db_session, "money@example.com")
    paid = await buy(client, root, user_id, "sca_1m", amount_total_pence=2499)
    await buy(client, root, user_id, "sca_1m")
    await ent_repo.grant(db_session, user_id=user_id, exam_id=exam.id, source="trial")
    await db_session.flush()

    grants = (await access_rows(client, root, user_id))["sca"]["grants"]
    by_source = {(grant["source"], grant["amount_total_pence"]): grant for grant in grants}
    assert sorted(by_source, key=str) == [("purchase", 0), ("purchase", 2499), ("trial", None)]
    bought = by_source[("purchase", 2499)]
    assert (bought["currency"], bought["receipt_id"], bought["payment_id"]) == (
        "gbp",
        paid["receipt_id"],
        paid["id"],
    )
    assert bought["paid_at"] is not None
    trial = by_source[("trial", None)]
    assert (trial["currency"], trial["paid_at"], trial["receipt_id"]) == (None, None, None)


async def test_a_free_payment_is_not_a_sale_in_revenue_or_the_paid_facet(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_sca_plan(db_session, "sca_1m", 30, 40)
    free_user = await a_buyer(db_session, "free@example.com")
    paid_user = await a_buyer(db_session, "paid@example.com")
    await buy(client, root, free_user, "sca_1m")
    await buy(client, root, paid_user, "sca_1m", amount_total_pence=1250)
    start = datetime.now(UTC) - timedelta(days=1)
    end = datetime.now(UTC) + timedelta(days=1)
    both = [free_user, paid_user]

    by_plan = await billing_service.revenue_breakdown_for_users(
        db_session, both, paid_from=start, paid_before=end
    )
    assert by_plan == [("sca_1m", 1, 1250)]
    over_time = await billing_service.revenue_over_time_for_users(
        db_session, both, paid_from=start, paid_before=end, bucket="day"
    )
    assert [(count, gross) for _, count, gross in over_time] == [(1, 1250)]
    assert await billing_service.payer_user_ids_among(db_session, both, paid_from=start, paid_before=end) == {
        paid_user
    }

    directory = await client.get("/api/v1/platform/directory?limit=100", headers=bearer(root))
    flags = {row["email"]: row["has_paid"] for row in directory.json()["items"]}
    assert (flags["free@example.com"], flags["paid@example.com"]) == (False, True)


async def test_a_stripe_settlement_queues_exactly_one_payment_receipt(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await a_plan(db_session)
    await a_customer(db_session, "webhook@example.com")
    event = checkout_event("evt_one_receipt", "webhook@example.com")
    assert (await post_event(client, event)).status_code == 200
    # Stripe retrying the same delivery must not queue a second email.
    await post_event(client, event)

    queued = await db_session.scalar(
        select(func.count())
        .select_from(OutboundMessage)
        .where(OutboundMessage.template_key == "payment_receipt")
    )
    assert queued == 1
