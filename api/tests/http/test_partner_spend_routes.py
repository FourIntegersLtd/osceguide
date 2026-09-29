"""A partner pilot's money: the ledger against Mixpanel, the spend estimate, and its alerts (G-1).

Ported from b2c's reconciliation and spend services. The ledger here is what a
partner is paid on and Mixpanel only corroborates it, so every Mixpanel outcome
— a count, no configuration, an error — has to come back as a report rather
than a refusal.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.growth import service_spend
from app.features.identity import repository as identity_repo
from app.features.notifications.models import OutboundMessage
from tests.http.test_growth_routes import arrive
from tests.support.catalog import ensure_exam
from tests.support.fakes import FakeEventCounts
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


@pytest.fixture(autouse=True)
async def the_pilot_exams(db_session: AsyncSession) -> None:
    for code in ("sca", "plab", "ortho"):
        await ensure_exam(db_session, code, partner_pilot=True)


def today() -> date:
    """Read at call time: `landed_at` is the transaction's own clock."""
    return datetime.now(UTC).date()


def with_event_counts(client: AsyncClient, fake: FakeEventCounts) -> FakeEventCounts:
    app = client._transport.app  # type: ignore[attr-defined]
    app.dependency_overrides[service_spend.get_event_counts] = lambda: fake
    return fake


async def test_the_ledger_is_set_beside_mixpanels_count(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root-recon@osceguide.com", platform_admin=True)
    for visitor in ("vk_a", "vk_b", "vk_c", "vk_d"):
        await arrive(client, visitor)
    await arrive(client, "vk_plab", ref_id="bmj-plab")
    mixpanel = with_event_counts(client, FakeEventCounts(count=3))

    response = await client.get(
        "/api/v1/growth/partners/bmj/reconciliation",
        params={"from_date": today().isoformat(), "to_date": today().isoformat(), "exam_code": "sca"},
        headers=bearer(root),
    )

    assert response.status_code == 200, response.text
    report = response.json()
    assert report["ledger_raw_count"] == 4
    assert report["mixpanel_raw_count"] == 3
    assert (report["delta"], report["delta_percent"]) == (1, 25.0)
    assert report["status"] == "ok"
    assert mixpanel.calls == [
        {
            "event": "partner_referral_landing",
            "from_date": today(),
            "to_date": today(),
            "where": {"partner": "bmj", "exam": "sca"},
        }
    ]


async def test_without_mixpanel_the_ledger_still_answers(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root-recon2@osceguide.com", platform_admin=True)
    await arrive(client, "vk_only")
    params = {"from_date": today().isoformat(), "to_date": today().isoformat()}

    with_event_counts(client, FakeEventCounts(unavailable="Mixpanel API secret not configured"))
    unconfigured = (
        await client.get("/api/v1/growth/partners/bmj/reconciliation", params=params, headers=bearer(root))
    ).json()
    assert (unconfigured["status"], unconfigured["ledger_raw_count"]) == ("mixpanel_unconfigured", 1)
    assert unconfigured["mixpanel_raw_count"] is None and unconfigured["delta"] is None

    with_event_counts(client, FakeEventCounts(fails="Mixpanel API error 500"))
    failed = (
        await client.get("/api/v1/growth/partners/bmj/reconciliation", params=params, headers=bearer(root))
    ).json()
    assert (failed["status"], failed["mixpanel_error"]) == ("mixpanel_error", "Mixpanel API error 500")


async def test_a_range_that_ends_before_it_starts_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root-recon3@osceguide.com", platform_admin=True)
    with_event_counts(client, FakeEventCounts())
    response = await client.get(
        "/api/v1/growth/partners/bmj/reconciliation",
        params={"from_date": "2026-09-10", "to_date": "2026-09-01"},
        headers=bearer(root),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_date_range"


async def test_the_money_routes_are_the_platforms_alone(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    someone = await make_actor("not-admin@example.com")
    params = {"from_date": today().isoformat(), "to_date": today().isoformat()}
    with_event_counts(client, FakeEventCounts())
    for path in ("reconciliation", "spend", "pilot-config"):
        response = await client.get(
            f"/api/v1/growth/partners/bmj/{path}", params=params, headers=bearer(someone)
        )
        assert response.status_code == 403, path


async def test_spend_is_every_arrival_at_the_pilots_rate_against_what_its_people_paid(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.billing import repository as billing_repo

    root = await make_actor("root-spend@osceguide.com", platform_admin=True)
    for visitor in ("vk_1", "vk_2", "vk_3"):
        await arrive(client, visitor)
    buyer = await make_actor("spend-buyer@example.com")
    await client.post("/api/v1/growth/acquisitions", json={"visitor_key": "vk_1"}, headers=bearer(buyer))
    user = await identity_repo.user_by_email(db_session, "spend-buyer@example.com")
    assert user is not None
    plan = await billing_repo.create_plan(
        db_session,
        code="spend-plan",
        stripe_price_id="price_spend",
        amount_pence=2499,
        duration_days=30,
        exam_code="sca",
    )
    await billing_repo.record_payment(
        db_session,
        user_id=user.id,
        plan_id=plan.id,
        stripe_payment_intent_id="pi_spend",
        checkout_session_id=None,
        amount_total_pence=2499,
        currency="gbp",
        receipt_url=None,
        paid_at=datetime.now(UTC),
        entitlement_id=None,
    )
    await db_session.commit()

    await client.patch(
        "/api/v1/growth/partners/bmj/pilot-config", json={"cost_per_click_pence": 50}, headers=bearer(root)
    )
    response = await client.get(
        "/api/v1/growth/partners/bmj/spend",
        params={"from_date": today().isoformat(), "to_date": today().isoformat()},
        headers=bearer(root),
    )

    assert response.status_code == 200, response.text
    spend = response.json()
    assert spend["estimated_click_count"] == 3
    assert spend["cost_per_click_pence"] == 50
    assert spend["estimated_spend_pence"] == 150
    assert spend["gross_revenue_pence"] == 2499
    assert spend["net_margin_pence"] == 2349
    assert (spend["acquired_user_count"], spend["cost_per_acquisition_pence"]) == (1, 150)
    assert "rough estimate" in spend["billing_disclaimer"]


async def test_the_pilot_config_starts_at_b2cs_defaults_and_keeps_what_is_sent(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root-config@osceguide.com", platform_admin=True)

    defaults = (await client.get("/api/v1/growth/partners/bmj/pilot-config", headers=bearer(root))).json()
    assert defaults == {
        "partner": "bmj",
        "cost_per_click_pence": 40,
        "spend_alert_thresholds_pence": [50_000, 100_000, 250_000],
        "spend_alert_recipients": [],
        "last_alerted_threshold_pence": 0,
    }

    updated = await client.patch(
        "/api/v1/growth/partners/bmj/pilot-config",
        json={
            "spend_alert_thresholds_pence": [2_000, 1_000, 2_000],
            "spend_alert_recipients": ["Ops@Example.com"],
        },
        headers=bearer(root),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["spend_alert_thresholds_pence"] == [1_000, 2_000]
    assert updated.json()["spend_alert_recipients"] == ["ops@example.com"]
    assert updated.json()["cost_per_click_pence"] == 40, "a field left out is unchanged"

    unknown = await client.get("/api/v1/growth/partners/nobody/pilot-config", headers=bearer(root))
    assert unknown.status_code == 404
    assert unknown.json()["code"] == "unknown_partner"


async def test_crossing_a_threshold_emails_once(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The daily job: three clicks at £1 is past a £2 threshold, not yet a £5 one.
    Run again, it does not alert the same threshold twice."""
    root = await make_actor("root-alert@osceguide.com", platform_admin=True)
    for visitor in ("vk_x", "vk_y", "vk_z"):
        await arrive(client, visitor)
    await client.patch(
        "/api/v1/growth/partners/bmj/pilot-config",
        json={
            "cost_per_click_pence": 100,
            "spend_alert_thresholds_pence": [100, 200, 500],
            "spend_alert_recipients": ["ops@example.com", "finance@example.com"],
        },
        headers=bearer(root),
    )

    assert await service_spend.check_spend_alerts(db_session, now=datetime.now(UTC)) == ["bmj"]
    assert await service_spend.check_spend_alerts(db_session, now=datetime.now(UTC)) == []

    alerts = list(
        (
            await db_session.execute(
                select(OutboundMessage).where(OutboundMessage.template_key == "partner_spend_alert")
            )
        ).scalars()
    )
    assert sorted(alert.recipient for alert in alerts) == ["finance@example.com", "ops@example.com"]
    assert all("£3.00" in alert.subject for alert in alerts)
    assert {alert.payload["threshold"] for alert in alerts} == {"£2.00"}
    config = (await client.get("/api/v1/growth/partners/bmj/pilot-config", headers=bearer(root))).json()
    assert config["last_alerted_threshold_pence"] == 200

    reset = await client.patch(
        "/api/v1/growth/partners/bmj/pilot-config", json={"reset_spend_alerts": True}, headers=bearer(root)
    )
    assert reset.json()["last_alerted_threshold_pence"] == 0


async def test_no_clicks_no_alert(db_session: AsyncSession) -> None:
    assert await service_spend.check_spend_alerts(db_session, now=datetime.now(UTC) + timedelta(days=1)) == []
