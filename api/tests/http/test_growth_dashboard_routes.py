"""The BMJ dashboard: an admin's full view of one partner pilot, and the
partner-safe reporting view of the same numbers with every revenue and
margin figure removed.

Written against `/api/v1/growth/partners/bmj/...`, the real Postgres and no
mocked Mixpanel — the adapter is unconfigured in tests, so every summary here
exercises the `mixpanel_unavailable` anomaly path rather than a live account.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import repository as billing_repo
from app.features.growth import repository
from app.features.identity import repository as identity_repo
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


def today() -> date:
    """Read at call time, like the funnel tests' `now()` — `landed_at` and
    `acquired_at` are Postgres transaction timestamps."""
    return datetime.now(UTC).date()


@pytest.fixture(autouse=True)
async def the_pilot_exams(db_session: AsyncSession) -> None:
    """Which exams are in the pilot, same fixture as the funnel tests."""
    for code in ("sca", "plab", "ortho"):
        await ensure_exam(db_session, code, partner_pilot=True)
    await ensure_exam(db_session, "casc", partner_pilot=False)


async def arrive(client: AsyncClient, visitor: str, ref_id: str = "bmj-sca") -> dict:
    """Same helper as the funnel tests: a visitor landing from a partner link."""
    response = await client.post(
        "/api/v1/growth/arrivals",
        json={"partner": "bmj", "visitor_key": visitor, "ref_id": ref_id},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def acquire(client: AsyncClient, token: str, visitor_key: str) -> None:
    """Credit a signed-in account to whoever sent them."""
    response = await client.post(
        "/api/v1/growth/acquisitions", json={"visitor_key": visitor_key}, headers=bearer(token)
    )
    assert response.status_code == 200, response.text


def date_range() -> dict[str, str]:
    """A range wide enough to hold everything a test creates: from a week ago
    to tomorrow, so a `landed_at`/`acquired_at` written at call time always
    falls inside it regardless of exactly when the request runs."""
    return {
        "from_date": (today() - timedelta(days=7)).isoformat(),
        "to_date": (today() + timedelta(days=1)).isoformat(),
    }


async def _pay(
    db_session: AsyncSession,
    *,
    user_id,
    plan_code: str | None,
    amount_pence: int,
    exam_code: str = "sca",
    paid_at: datetime | None = None,
) -> None:
    """Record a settled payment for a user, optionally against a plan row
    (or `None` to prove a deleted plan's payment still counts, under "unknown")."""
    plan_id = None
    if plan_code is not None:
        plan = await billing_repo.create_plan(
            db_session,
            code=plan_code,
            stripe_price_id=f"price_{plan_code}",
            amount_pence=amount_pence,
            duration_days=30,
            exam_code=exam_code,
        )
        plan_id = plan.id
    await billing_repo.record_payment(
        db_session,
        user_id=user_id,
        plan_id=plan_id,
        stripe_payment_intent_id=f"pi_{plan_code or 'deleted'}_{user_id}",
        checkout_session_id=None,
        amount_total_pence=amount_pence,
        currency="gbp",
        receipt_url=None,
        paid_at=paid_at or datetime.now(UTC),
        entitlement_id=None,
    )
    await db_session.commit()


# --- admin summary -----------------------------------------------------------


async def test_the_admin_summary_counts_arrivals_signups_and_revenue(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("dash-admin-summary@osceguide.com", platform_admin=True)
    await arrive(client, "dash-visitor-1")
    buyer = await make_actor("dash-buyer-1@example.com")
    await acquire(client, buyer, "dash-visitor-1")
    user = await identity_repo.user_by_email(db_session, "dash-buyer-1@example.com")
    assert user is not None
    await _pay(db_session, user_id=user.id, plan_code="dash-plan-1", amount_pence=2999)

    response = await client.get(
        "/api/v1/growth/partners/bmj/summary", params=date_range(), headers=bearer(admin)
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["partner"] == "bmj"
    assert body["raw_arrival_count"] >= 1
    assert body["acquired_user_count"] >= 1
    assert body["revenue"]["gross_revenue_pence"] >= 2999
    assert body["revenue"]["paying_user_count"] >= 1
    # No Mixpanel account in tests: the reconciliation could not be corroborated,
    # so the anomaly panel flags it rather than silently comparing to nothing.
    assert body["reconciliation"]["status"] == "mixpanel_unconfigured"
    codes = {item["code"] for item in body["anomalies"]["items"]}
    assert "mixpanel_unavailable" in codes


async def test_a_payment_whose_plan_has_been_deleted_counts_as_unknown(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """`Payment.plan_id` is `SET NULL`, so a retired plan's payment must still
    show up in the revenue breakdown, under a plan code of `"unknown"`."""
    admin = await make_actor("dash-admin-deleted-plan@osceguide.com", platform_admin=True)
    await arrive(client, "dash-visitor-deleted-plan")
    buyer = await make_actor("dash-buyer-deleted-plan@example.com")
    await acquire(client, buyer, "dash-visitor-deleted-plan")
    user = await identity_repo.user_by_email(db_session, "dash-buyer-deleted-plan@example.com")
    assert user is not None
    await _pay(db_session, user_id=user.id, plan_code=None, amount_pence=1500)

    response = await client.get(
        "/api/v1/growth/partners/bmj/revenue", params=date_range(), headers=bearer(admin)
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["gross_revenue_pence"] >= 1500
    plan_codes = {row["plan_type"] for row in body["revenue_by_plan"]}
    assert "unknown" in plan_codes


async def test_an_exam_filter_narrows_the_summary(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("dash-admin-exam-filter@osceguide.com", platform_admin=True)
    await arrive(client, "dash-visitor-sca-filter", ref_id="bmj-sca")
    await arrive(client, "dash-visitor-plab-filter", ref_id="bmj-plab")

    sca_only = await client.get(
        "/api/v1/growth/partners/bmj/summary",
        params={**date_range(), "exam_code": "sca"},
        headers=bearer(admin),
    )
    assert sca_only.status_code == 200, sca_only.text
    assert sca_only.json()["exam_code"] == "sca"

    unfiltered = await client.get(
        "/api/v1/growth/partners/bmj/summary", params=date_range(), headers=bearer(admin)
    )
    assert unfiltered.json()["raw_arrival_count"] >= sca_only.json()["raw_arrival_count"]


async def test_a_range_with_no_arrivals_is_all_zeros_not_an_error(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("dash-admin-empty-range@osceguide.com", platform_admin=True)
    long_ago = {"from_date": "2000-01-01", "to_date": "2000-01-02"}

    response = await client.get("/api/v1/growth/partners/bmj/summary", params=long_ago, headers=bearer(admin))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["raw_arrival_count"] == 0
    assert body["acquired_user_count"] == 0
    assert body["revenue"]["gross_revenue_pence"] == 0


async def test_an_inverted_range_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("dash-admin-inverted@osceguide.com", platform_admin=True)
    response = await client.get(
        "/api/v1/growth/partners/bmj/summary",
        params={"from_date": "2026-02-01", "to_date": "2026-01-01"},
        headers=bearer(admin),
    )
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "invalid_date_range"


async def test_only_a_platform_admin_reads_the_dashboard_summary(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("dash-not-admin@example.com")
    response = await client.get(
        "/api/v1/growth/partners/bmj/summary", params=date_range(), headers=bearer(token)
    )
    assert response.status_code == 403


# --- bucketed charts, gap-filled ---------------------------------------------


async def test_revenue_over_time_fills_the_gaps_between_paid_buckets(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Only the days with a payment come back from the database; the rest of
    the range must still appear, at zero, so a chart's x-axis is continuous."""
    admin = await make_actor("dash-admin-revenue-chart@osceguide.com", platform_admin=True)
    await arrive(client, "dash-visitor-chart")
    buyer = await make_actor("dash-buyer-chart@example.com")
    await acquire(client, buyer, "dash-visitor-chart")
    user = await identity_repo.user_by_email(db_session, "dash-buyer-chart@example.com")
    assert user is not None
    await _pay(db_session, user_id=user.id, plan_code="dash-plan-chart", amount_pence=1000)

    response = await client.get(
        "/api/v1/growth/partners/bmj/revenue-over-time",
        params={**date_range(), "bucket": "day"},
        headers=bearer(admin),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    from_date = date.fromisoformat(body["from_date"])
    to_date = date.fromisoformat(body["to_date"])
    expected_days = (to_date - from_date).days + 1
    assert len(body["points"]) == expected_days
    total_revenue = sum(point["gross_revenue_pence"] for point in body["points"])
    assert total_revenue >= 1000
    # Every point on a day nobody paid is zero, not missing.
    zero_days = [point for point in body["points"] if point["gross_revenue_pence"] == 0]
    assert len(zero_days) == expected_days - 1


async def test_an_invalid_bucket_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("dash-admin-bad-bucket@osceguide.com", platform_admin=True)
    response = await client.get(
        "/api/v1/growth/partners/bmj/revenue-over-time",
        params={**date_range(), "bucket": "fortnight"},
        headers=bearer(admin),
    )
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "invalid_bucket"


# --- arrivals and acquired-users tables --------------------------------------


async def test_the_arrivals_table_is_searchable_by_visitor_key(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("dash-admin-arrivals-search@osceguide.com", platform_admin=True)
    await arrive(client, "findable-visitor-xyz")
    await arrive(client, "someone-else-entirely")

    response = await client.get(
        "/api/v1/growth/partners/bmj/arrivals",
        params={**date_range(), "search": "findable"},
        headers=bearer(admin),
    )

    assert response.status_code == 200, response.text
    rows = response.json()["items"]
    assert len(rows) == 1
    assert rows[0]["visitor_key"] == "findable-visitor-xyz"


async def test_the_acquired_users_table_carries_the_arrivals_utm_tags(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("dash-admin-acquired-users@osceguide.com", platform_admin=True)
    response = await client.post(
        "/api/v1/growth/arrivals",
        json={
            "partner": "bmj",
            "visitor_key": "dash-visitor-utm",
            "ref_id": "bmj-sca",
            "utm": {"utm_campaign": "spring-push", "utm_medium": "email"},
        },
    )
    assert response.status_code == 201, response.text
    buyer = await make_actor("dash-buyer-utm@example.com")
    await acquire(client, buyer, "dash-visitor-utm")

    rows_response = await client.get(
        "/api/v1/growth/partners/bmj/acquired-users", params=date_range(), headers=bearer(admin)
    )

    assert rows_response.status_code == 200, rows_response.text
    rows = rows_response.json()["items"]
    matching = [row for row in rows if row["visitor_key"] == "dash-visitor-utm"]
    assert len(matching) == 1
    assert matching[0]["utm_campaign"] == "spring-push"
    assert matching[0]["utm_medium"] == "email"
    assert matching[0]["original_ref_id"] == "bmj-sca"


# --- reporters (admin Access tab) ---------------------------------------------


async def test_the_admin_lists_and_revokes_a_reporter(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("dash-admin-reporters@osceguide.com", platform_admin=True)
    await repository.add_reporter(db_session, partner="bmj", email="revoke-me@bmj.com")
    await db_session.commit()

    listed = await client.get("/api/v1/growth/partners/bmj/reporters", headers=bearer(admin))
    assert listed.status_code == 200, listed.text
    emails = {row["email"] for row in listed.json()}
    assert "revoke-me@bmj.com" in emails
    assert next(row for row in listed.json() if row["email"] == "revoke-me@bmj.com")["revoked_at"] is None

    revoked = await client.delete(
        "/api/v1/growth/partners/bmj/reporters/revoke-me@bmj.com", headers=bearer(admin)
    )
    assert revoked.status_code == 204, revoked.text

    relisted = await client.get("/api/v1/growth/partners/bmj/reporters", headers=bearer(admin))
    row = next(row for row in relisted.json() if row["email"] == "revoke-me@bmj.com")
    assert row["revoked_at"] is not None


async def test_revoking_an_unknown_reporter_is_a_named_404(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("dash-admin-revoke-unknown@osceguide.com", platform_admin=True)
    response = await client.delete(
        "/api/v1/growth/partners/bmj/reporters/never-existed@bmj.com", headers=bearer(admin)
    )
    assert response.status_code == 404, response.text
    assert response.json()["code"] == "reporter_not_found"


async def test_a_revoked_reporter_can_no_longer_read_the_funnel(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Revoking access must take effect immediately, not just stop a future grant."""
    admin = await make_actor("dash-admin-revoke-effect@osceguide.com", platform_admin=True)
    reporter_token = await make_actor("was-reporter@bmj.com")
    await repository.add_reporter(db_session, partner="bmj", email="was-reporter@bmj.com")
    await db_session.commit()

    still_allowed = await client.get("/api/v1/growth/partners/bmj/funnel", headers=bearer(reporter_token))
    assert still_allowed.status_code == 200, still_allowed.text

    await client.delete("/api/v1/growth/partners/bmj/reporters/was-reporter@bmj.com", headers=bearer(admin))

    refused = await client.get("/api/v1/growth/partners/bmj/funnel", headers=bearer(reporter_token))
    assert refused.status_code == 403, refused.text
    assert refused.json()["code"] == "not_a_partner_reporter"


# --- partner mode: reporting/* never returns money ---------------------------


async def test_the_partner_summary_never_carries_revenue_or_margin(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    reporter = await make_actor("dash-reporter-no-money@bmj.com")
    await repository.add_reporter(db_session, partner="bmj", email="dash-reporter-no-money@bmj.com")
    await db_session.commit()
    await arrive(client, "dash-visitor-no-money")
    buyer = await make_actor("dash-buyer-no-money@example.com")
    await acquire(client, buyer, "dash-visitor-no-money")
    user = await identity_repo.user_by_email(db_session, "dash-buyer-no-money@example.com")
    assert user is not None
    await _pay(db_session, user_id=user.id, plan_code="dash-plan-no-money", amount_pence=4999)

    response = await client.get(
        "/api/v1/growth/partners/bmj/reporting/summary", params=date_range(), headers=bearer(reporter)
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["paying_user_count"] >= 1
    # The strict business rule under test: no money anywhere in this payload.
    assert "revenue" not in body
    assert "gross_revenue_pence" not in body
    assert "net_margin_pence" not in body
    assert "spend" not in body
    assert body["fee"]["estimated_spend_pence"] >= 0
    assert set(body["fee"].keys()) == {
        "estimated_click_count",
        "cost_per_click_pence",
        "estimated_spend_pence",
        "billing_disclaimer",
        "currency",
        "click_count_source",
    }


async def test_the_partner_breakdown_counts_visits_signups_and_payments_by_exam(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    reporter = await make_actor("dash-reporter-breakdown@bmj.com")
    await repository.add_reporter(db_session, partner="bmj", email="dash-reporter-breakdown@bmj.com")
    await db_session.commit()
    await arrive(client, "dash-visitor-breakdown-sca", ref_id="bmj-sca")
    await arrive(client, "dash-visitor-breakdown-plab", ref_id="bmj-plab")
    buyer = await make_actor("dash-buyer-breakdown@example.com")
    await acquire(client, buyer, "dash-visitor-breakdown-sca")

    response = await client.get(
        "/api/v1/growth/partners/bmj/reporting/summary", params=date_range(), headers=bearer(reporter)
    )

    assert response.status_code == 200, response.text
    by_exam = {row["dimension"]: row for row in response.json()["breakdown_by_exam"]}
    assert by_exam["sca"]["visit_count"] >= 1
    assert by_exam["sca"]["signup_count"] >= 1
    assert by_exam["plab"]["visit_count"] >= 1
    assert by_exam["plab"]["signup_count"] == 0


async def test_paid_counts_follow_the_arrivals_exam_and_campaign_and_the_payment_range(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """b2c `build_partner_breakdowns`: a sign-up is "paid" when that user has a
    payment inside the range, counted under the exam and campaign of their
    *arrival*, never the plan's."""
    reporter = await make_actor("dash-reporter-paid@bmj.com")
    await repository.add_reporter(db_session, partner="bmj", email="dash-reporter-paid@bmj.com")
    await db_session.commit()
    cases = [
        ("paid-a", "bmj-sca", "paid-spring", True),
        ("paid-b", "bmj-sca", "paid-newsletter", False),
        ("paid-c", "bmj-plab", "paid-spring", True),
        ("paid-d", "bmj-plab", "paid-newsletter", "outside"),
    ]
    for name, ref_id, campaign, _paid in cases:
        response = await client.post(
            "/api/v1/growth/arrivals",
            json={
                "partner": "bmj",
                "visitor_key": f"dash-{name}",
                "ref_id": ref_id,
                "utm": {"utm_campaign": campaign},
            },
        )
        assert response.status_code == 201, response.text
        token = await make_actor(f"dash-{name}@example.com")
        await acquire(client, token, f"dash-{name}")
    for name, _ref, _campaign, paid in cases:
        if paid is False:
            continue
        user = await identity_repo.user_by_email(db_session, f"dash-{name}@example.com")
        assert user is not None
        await _pay(
            db_session,
            user_id=user.id,
            plan_code=f"plan-{name}",
            amount_pence=2499,
            exam_code="sca",
            paid_at=datetime.now(UTC) - timedelta(days=30) if paid == "outside" else None,
        )

    response = await client.get(
        "/api/v1/growth/partners/bmj/reporting/summary", params=date_range(), headers=bearer(reporter)
    )

    assert response.status_code == 200, response.text
    body = response.json()
    by_exam = {
        row["dimension"]: (row["signup_count"], row["paid_count"]) for row in body["breakdown_by_exam"]
    }
    by_campaign = {
        row["dimension"]: (row["signup_count"], row["paid_count"]) for row in body["breakdown_by_campaign"]
    }
    assert by_exam["sca"] == (2, 1)
    assert by_exam["plab"] == (2, 1)
    assert by_campaign["paid-spring"] == (2, 2)
    assert by_campaign["paid-newsletter"] == (2, 0)
    assert body["paying_user_count"] == 2


async def test_the_exam_and_campaign_filters_narrow_every_breakdown_count(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """b2c `aggregate_partner_breakdowns` narrows arrivals and sign-ups by
    `exam` and `utm_campaign`; the unfiltered table is the control."""
    reporter = await make_actor("dash-reporter-filter@bmj.com")
    await repository.add_reporter(db_session, partner="bmj", email="dash-reporter-filter@bmj.com")
    await db_session.commit()
    cases = [
        ("filt-a", "bmj-sca", "filt-spring", True),
        ("filt-b", "bmj-sca", "filt-newsletter", False),
        ("filt-c", "bmj-plab", "filt-spring", True),
        ("filt-d", "bmj-plab", "filt-newsletter", False),
    ]
    for name, ref_id, campaign, paid in cases:
        response = await client.post(
            "/api/v1/growth/arrivals",
            json={
                "partner": "bmj",
                "visitor_key": f"dash-{name}",
                "ref_id": ref_id,
                "utm": {"utm_campaign": campaign},
            },
        )
        assert response.status_code == 201, response.text
        token = await make_actor(f"dash-{name}@example.com")
        await acquire(client, token, f"dash-{name}")
        if paid:
            user = await identity_repo.user_by_email(db_session, f"dash-{name}@example.com")
            assert user is not None
            await _pay(db_session, user_id=user.id, plan_code=f"plan-{name}", amount_pence=2499)

    async def breakdown(**filters: str) -> dict:
        response = await client.get(
            "/api/v1/growth/partners/bmj/reporting/summary",
            params={**date_range(), **filters},
            headers=bearer(reporter),
        )
        assert response.status_code == 200, response.text
        return response.json()

    def counts(rows: list[dict]) -> dict[str, tuple[int, int, int]]:
        return {
            row["dimension"]: (row["visit_count"], row["signup_count"], row["paid_count"]) for row in rows
        }

    unfiltered = await breakdown()
    assert counts(unfiltered["breakdown_by_campaign"])["filt-newsletter"] == (2, 2, 0)
    assert counts(unfiltered["breakdown_by_campaign"])["filt-spring"] == (2, 2, 2)

    by_campaign = await breakdown(utm_campaign="filt-spring")
    assert counts(by_campaign["breakdown_by_campaign"]) == {"filt-spring": (2, 2, 2)}
    assert counts(by_campaign["breakdown_by_exam"]) == {"sca": (1, 1, 1), "plab": (1, 1, 1)}

    by_exam = await breakdown(exam_code="plab")
    assert counts(by_exam["breakdown_by_exam"]) == {"plab": (2, 2, 1)}
    assert counts(by_exam["breakdown_by_campaign"]) == {
        "filt-newsletter": (1, 1, 0),
        "filt-spring": (1, 1, 1),
    }

    both = await breakdown(exam_code="sca", utm_campaign="filt-newsletter")
    assert counts(both["breakdown_by_exam"]) == {"sca": (1, 1, 0)}
    assert counts(both["breakdown_by_campaign"]) == {"filt-newsletter": (1, 1, 0)}


async def test_visits_and_signups_over_time_carry_no_money_either(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    reporter = await make_actor("dash-reporter-charts@bmj.com")
    await repository.add_reporter(db_session, partner="bmj", email="dash-reporter-charts@bmj.com")
    await db_session.commit()
    await arrive(client, "dash-visitor-charts")

    visits = await client.get(
        "/api/v1/growth/partners/bmj/reporting/visits-over-time",
        params={**date_range(), "bucket": "day"},
        headers=bearer(reporter),
    )
    signups = await client.get(
        "/api/v1/growth/partners/bmj/reporting/signups-over-time",
        params={**date_range(), "bucket": "day"},
        headers=bearer(reporter),
    )
    fee = await client.get(
        "/api/v1/growth/partners/bmj/reporting/fee-over-time",
        params={**date_range(), "bucket": "day"},
        headers=bearer(reporter),
    )

    assert visits.status_code == 200, visits.text
    assert signups.status_code == 200, signups.text
    assert fee.status_code == 200, fee.text
    assert sum(point["count"] for point in visits.json()["points"]) >= 1
    assert "gross_revenue_pence" not in str(fee.json())
    assert all("visit_count" in point and "estimated_fee_pence" in point for point in fee.json()["points"])


async def test_a_non_reporter_is_refused_every_reporting_route(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("dash-not-a-reporter@example.com")
    for path in (
        "/api/v1/growth/partners/bmj/reporting/summary",
        "/api/v1/growth/partners/bmj/reporting/visits-over-time",
        "/api/v1/growth/partners/bmj/reporting/signups-over-time",
        "/api/v1/growth/partners/bmj/reporting/fee-over-time",
    ):
        response = await client.get(path, params={**date_range(), "bucket": "day"}, headers=bearer(token))
        assert response.status_code == 403, f"{path}: {response.text}"
        assert response.json()["code"] == "not_a_partner_reporter"


# --- the funnel's new filters and steps --------------------------------------


async def test_the_funnel_accepts_a_range_and_reports_its_steps(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("dash-admin-funnel-steps@osceguide.com", platform_admin=True)
    await arrive(client, "dash-visitor-funnel-steps")

    response = await client.get(
        "/api/v1/growth/partners/bmj/funnel", params=date_range(), headers=bearer(admin)
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["arrivals"] >= 1
    steps = {step["step"]: step["count"] for step in body["steps"]}
    assert steps["arrivals"] == body["arrivals"]
    assert steps["signups"] == body["signups"]
    assert steps["purchases"] == body["purchases"]


async def test_the_funnel_requires_both_dates_when_filtering(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("dash-admin-funnel-partial-range@osceguide.com", platform_admin=True)
    response = await client.get(
        "/api/v1/growth/partners/bmj/funnel",
        params={"exam_code": "sca"},
        headers=bearer(admin),
    )
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "invalid_date_range"


# --- a partner organisation's admin reads its own dashboard (H-2) -------------


async def _partner_org_admin(
    db_session: AsyncSession, make_actor, *, email: str, slug: str, role: str = "partner_admin"
) -> str:  # type: ignore[no-untyped-def]
    from app.core.auth import Membership
    from app.features.tenancy import repository as tenancy_repo

    org = await tenancy_repo.organization_by_slug(db_session, slug)
    if org is None:
        org = await tenancy_repo.create_organization(db_session, slug=slug, name=slug, org_type="partner")
    token = await make_actor(
        email, memberships=(Membership(org_id=org.id, org_slug=slug, role=role, surface=None),)
    )
    await db_session.commit()
    return token


async def test_a_partner_admin_reads_its_own_dashboard_without_a_reporter_grant(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    for slug in ("bmj", "wiley"):
        token = await _partner_org_admin(db_session, make_actor, email=f"pa-{slug}@example.com", slug=slug)
        response = await client.get(
            f"/api/v1/growth/partners/{slug}/reporting/summary", params=date_range(), headers=bearer(token)
        )
        assert response.status_code == 200, f"{slug}: {response.text}"


async def test_only_an_admin_of_that_partner_org_reads_it(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    member = await _partner_org_admin(
        db_session, make_actor, email="pa-member@example.com", slug="wiley", role="member"
    )
    other_admin = await _partner_org_admin(
        db_session, make_actor, email="pa-other@example.com", slug="elsevier"
    )
    for token in (member, other_admin):
        response = await client.get(
            "/api/v1/growth/partners/wiley/reporting/summary", params=date_range(), headers=bearer(token)
        )
        assert response.status_code == 403, response.text
        assert response.json()["code"] == "not_a_partner_reporter"


async def test_a_suspended_partner_org_or_a_revoked_admin_is_refused(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    from app.features.tenancy import repository as tenancy_repo

    suspended = await _partner_org_admin(db_session, make_actor, email="pa-susp@example.com", slug="gone")
    org = await tenancy_repo.organization_by_slug(db_session, "gone")
    assert org is not None
    await tenancy_repo.set_organization_status(db_session, org.id, status="suspended")
    revoked = await _partner_org_admin(db_session, make_actor, email="pa-rev@example.com", slug="kept")
    kept = await tenancy_repo.organization_by_slug(db_session, "kept")
    user = await identity_repo.user_by_email(db_session, "pa-rev@example.com")
    assert kept is not None and user is not None
    (membership,) = await tenancy_repo.memberships_for_user_in_org(db_session, kept.id, user.id)
    await tenancy_repo.set_membership_revoked(db_session, kept.id, membership.id, at=datetime.now(UTC))
    await db_session.commit()
    for token, slug in ((suspended, "gone"), (revoked, "kept")):
        response = await client.get(
            f"/api/v1/growth/partners/{slug}/reporting/summary", params=date_range(), headers=bearer(token)
        )
        assert response.status_code == 403, f"{slug}: {response.text}"


async def test_a_key_that_is_no_pilot_and_no_partner_org_is_unknown(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("pa-root@example.com", platform_admin=True)
    response = await client.get(
        "/api/v1/growth/partners/nobody/reporting/summary", params=date_range(), headers=bearer(admin)
    )
    assert response.status_code == 404, response.text
    assert response.json()["code"] == "unknown_partner"


async def test_a_partner_org_admin_reads_its_own_funnel(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token = await _partner_org_admin(db_session, make_actor, email="pa-funnel@example.com", slug="wiley")
    response = await client.get("/api/v1/growth/partners/wiley/funnel", headers=bearer(token))
    assert response.status_code == 200, response.text
    other = await client.get("/api/v1/growth/partners/bmj/funnel", headers=bearer(token))
    assert other.status_code == 403, other.text
