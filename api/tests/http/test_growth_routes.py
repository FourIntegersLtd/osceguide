"""Attribution and referrals — where the numbers decide what is owed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.growth import repository, service
from app.features.identity import repository as identity_repo
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


def now() -> datetime:
    """Read at call time. `landed_at` is a Postgres transaction timestamp, and
    attribution only runs forwards, so a clock fixed at import is behind every
    arrival it is asked about and credits nobody."""
    return datetime.now(UTC)


@pytest.fixture(autouse=True)
async def the_pilot_exams(db_session: AsyncSession) -> None:
    """Which exams are in the pilot is `exams.partner_pilot` now, not a tuple
    in the growth domain — so a test that expects three references has to say
    which three, and one that expects CASC excluded has to leave it out."""
    for code in ("sca", "plab", "ortho"):
        await ensure_exam(db_session, code, partner_pilot=True)
    await ensure_exam(db_session, "casc", partner_pilot=False)


async def arrive(client: AsyncClient, visitor: str, ref_id: str = "bmj-sca") -> dict:
    response = await client.post(
        "/api/v1/growth/arrivals",
        json={"partner": "bmj", "visitor_key": visitor, "ref_id": ref_id},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_an_arrival_needs_no_account(client: AsyncClient) -> None:
    """There is nobody to authenticate yet."""
    body = await arrive(client, "vk_1")
    assert body["partner"] == "bmj"
    assert body["exam_code"] == "sca"


async def test_an_unknown_partner_is_refused(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/growth/arrivals",
        json={"partner": "someone-else", "visitor_key": "vk_2"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_partner"


async def test_an_unrecognised_reference_credits_nobody_an_exam(client: AsyncClient) -> None:
    """Guessing is worse than declining: the cost is money owed to the wrong
    party."""
    body = await arrive(client, "vk_3", ref_id="bmj-casc")
    assert body["exam_code"] is None


async def test_a_signup_is_credited_to_the_partner(client: AsyncClient, db_session: AsyncSession) -> None:
    await arrive(client, "vk_4")
    user = await identity_repo.create_user(
        session=db_session, email="att@example.com", name="A", password_hash=None
    )
    await db_session.flush()

    acquired = await service.attribute_signup(db_session, user_id=user.id, visitor_key="vk_4", now=now())
    assert acquired is not None
    assert acquired.partner == "bmj"


async def test_a_second_attribution_does_not_overwrite_the_first(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Re-attributing a user because they later clicked another link is how the
    numbers stop reconciling."""
    await arrive(client, "vk_5")
    user = await identity_repo.create_user(
        session=db_session, email="once@example.com", name="O", password_hash=None
    )
    await db_session.flush()

    first = await service.attribute_signup(db_session, user_id=user.id, visitor_key="vk_5", now=now())
    assert first is not None
    second = await service.attribute_signup(db_session, user_id=user.id, visitor_key="vk_5", now=now())
    assert second is None


async def test_an_arrival_outside_the_window_is_not_credited(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await arrive(client, "vk_6")
    user = await identity_repo.create_user(
        session=db_session, email="stale@example.com", name="S", password_hash=None
    )
    await db_session.flush()
    much_later = now() + timedelta(days=200)
    assert (
        await service.attribute_signup(db_session, user_id=user.id, visitor_key="vk_6", now=much_later)
        is None
    )


async def test_signing_up_with_no_arrival_credits_nobody(db_session: AsyncSession) -> None:
    """The normal case. Silence, not an error."""
    user = await identity_repo.create_user(
        session=db_session, email="organic@example.com", name="O", password_hash=None
    )
    await db_session.flush()
    assert await service.attribute_signup(db_session, user_id=user.id, visitor_key=None, now=now()) is None


async def test_a_reporter_reads_their_own_partners_funnel(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("reporter@bmj.com")
    await repository.add_reporter(db_session, partner="bmj", email="reporter@bmj.com")
    await db_session.flush()
    await arrive(client, "vk_7")

    response = await client.get("/api/v1/growth/partners/bmj/funnel", headers=bearer(token))
    assert response.status_code == 200
    assert response.json()["arrivals"] >= 1


async def test_someone_who_is_not_a_reporter_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("nosy@example.com")
    response = await client.get("/api/v1/growth/partners/bmj/funnel", headers=bearer(token))
    assert response.status_code == 403
    assert response.json()["code"] == "not_a_partner_reporter"


async def test_a_referral_code_is_issued_once(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("ref@example.com")
    first = await client.post("/api/v1/me/referral-code", headers=bearer(token))
    second = await client.post("/api/v1/me/referral-code", headers=bearer(token))
    assert first.json()["code"] == second.json()["code"]


async def test_you_cannot_refer_yourself(client: AsyncClient, db_session: AsyncSession, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("self@example.com")
    code = (await client.post("/api/v1/me/referral-code", headers=bearer(token))).json()["code"]
    user = await identity_repo.user_by_email(db_session, "self@example.com")
    assert user is not None

    from app.features.growth.errors import ReferralNotFound

    with pytest.raises(ReferralNotFound):
        await service.redeem_code(
            db_session, code=code, referred_user_id=user.id, earned_pence=500, now=now()
        )


async def test_a_signup_is_credited_to_the_partner_who_sent_them(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """`attribute_signup` had no caller anywhere, so the acquisition table was
    never written and every partner funnel reported zero signups forever."""
    await arrive(client, "visitor-credited")
    token = await make_actor("credited@example.com")

    credited = await client.post(
        "/api/v1/growth/acquisitions",
        json={"visitor_key": "visitor-credited"},
        headers=bearer(token),
    )
    assert credited.status_code == 200, credited.text
    assert credited.json()["partner"] == "bmj"
    assert credited.json()["exam_code"] == "sca"


async def test_crediting_twice_credits_once(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    await arrive(client, "visitor-twice")
    token = await make_actor("twice@example.com")
    url = "/api/v1/growth/acquisitions"
    body = {"visitor_key": "visitor-twice"}

    first = await client.post(url, json=body, headers=bearer(token))
    second = await client.post(url, json=body, headers=bearer(token))
    assert first.json() is not None
    assert second.json() is None, "a second credit for the same person is not a second acquisition"


async def test_signing_up_without_a_partner_credits_nobody(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("organic@example.com")
    response = await client.post(
        "/api/v1/growth/acquisitions", json={"visitor_key": "never-arrived"}, headers=bearer(token)
    )
    assert response.status_code == 200
    assert response.json() is None


async def test_a_referral_code_can_be_redeemed(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Codes were issued and there was no route to redeem one, so `earned_pence`
    could only ever be zero."""
    referrer = await make_actor("referrer@example.com")
    issued = await client.post("/api/v1/me/referral-code", headers=bearer(referrer))
    code = issued.json()["code"]

    friend = await make_actor("friend@example.com")
    redeemed = await client.post("/api/v1/me/referrals/redeem", json={"code": code}, headers=bearer(friend))
    assert redeemed.status_code == 200, redeemed.text

    mine = await client.get("/api/v1/me/referrals", headers=bearer(referrer))
    assert mine.json()["redeemed_count"] == 1
    assert mine.json()["earned_pence"] > 0


async def test_a_code_cannot_be_redeemed_twice(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    referrer = await make_actor("referrer2@example.com")
    code = (await client.post("/api/v1/me/referral-code", headers=bearer(referrer))).json()["code"]
    first_friend = await make_actor("friend2a@example.com")
    second_friend = await make_actor("friend2b@example.com")

    await client.post("/api/v1/me/referrals/redeem", json={"code": code}, headers=bearer(first_friend))
    again = await client.post(
        "/api/v1/me/referrals/redeem", json={"code": code}, headers=bearer(second_friend)
    )
    assert again.status_code == 409
    assert again.json()["code"] == "referral_already_redeemed"


async def test_redeeming_your_own_code_is_not_a_referral(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("selfref@example.com")
    code = (await client.post("/api/v1/me/referral-code", headers=bearer(token))).json()["code"]
    response = await client.post("/api/v1/me/referrals/redeem", json={"code": code}, headers=bearer(token))
    assert response.status_code == 404


async def test_a_partner_reporter_can_be_appointed_and_reads_the_funnel(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """There was no way to create a reporter, so the funnel was readable by
    platform admins alone — which is not what a partner report is for."""
    root = await make_actor("root-growth@osceguide.com", platform_admin=True)
    reporter_token = await make_actor("reporter@bmj.com")

    refused = await client.get("/api/v1/growth/partners/bmj/funnel", headers=bearer(reporter_token))
    assert refused.status_code == 403
    assert refused.json()["code"] == "not_a_partner_reporter"

    appointed = await client.post(
        "/api/v1/growth/partners/bmj/reporters",
        json={"email": "reporter@bmj.com"},
        headers=bearer(root),
    )
    assert appointed.status_code == 204, appointed.text

    allowed = await client.get("/api/v1/growth/partners/bmj/funnel", headers=bearer(reporter_token))
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["partner"] == "bmj"
    assert allowed.json()["purchases"] == 0


async def test_only_a_platform_admin_appoints_a_reporter(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("not-admin-growth@example.com")
    response = await client.post(
        "/api/v1/growth/partners/bmj/reporters", json={"email": "x@bmj.com"}, headers=bearer(token)
    )
    assert response.status_code == 403


async def test_the_funnel_counts_what_a_partners_people_have_paid(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """`purchases` was a parameter defaulted to zero that no caller ever
    passed, so the purchase rate was structurally 0.0 (G-2)."""
    from app.features.billing import repository as billing_repo

    root = await make_actor("root-funnel@osceguide.com", platform_admin=True)
    await arrive(client, "visitor-buyer")
    buyer = await make_actor("buyer-funnel@example.com")
    await client.post(
        "/api/v1/growth/acquisitions", json={"visitor_key": "visitor-buyer"}, headers=bearer(buyer)
    )

    user = await identity_repo.user_by_email(db_session, "buyer-funnel@example.com")
    assert user is not None
    plan = await billing_repo.create_plan(
        db_session,
        code="funnel-plan",
        stripe_price_id="price_funnel",
        amount_pence=2499,
        duration_days=30,
        exam_code="sca",
    )
    await billing_repo.record_payment(
        db_session,
        user_id=user.id,
        plan_id=plan.id,
        stripe_payment_intent_id="pi_funnel",
        checkout_session_id=None,
        amount_total_pence=2499,
        currency="gbp",
        receipt_url=None,
        paid_at=now(),
        entitlement_id=None,
    )
    await db_session.commit()

    funnel = await client.get("/api/v1/growth/partners/bmj/funnel", headers=bearer(root))
    assert funnel.status_code == 200, funnel.text
    assert funnel.json()["purchases"] == 1
    assert funnel.json()["purchase_rate"] > 0


async def test_a_reporter_reads_the_references_they_put_in_their_links(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The other half of `parse_ref_id`, which had no route at all.

    A partner was told the spelling in an email and typed `bmj-sca` by hand,
    and a typo attributes their traffic to nobody — silently, which is what
    this slice exists to prevent.
    """
    token = await make_actor("links@bmj.com")
    await repository.add_reporter(db_session, partner="bmj", email="links@bmj.com")
    await db_session.flush()

    response = await client.get("/api/v1/growth/partners/bmj/ref-ids", headers=bearer(token))
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    # Sorted by code, because the set comes from the table rather than from a
    # tuple whose order was somebody's preference.
    assert [row["ref_id"] for row in items] == ["bmj-ortho", "bmj-plab", "bmj-sca"]
    assert items[0]["landing_path"] == "/exams/ortho"

    # The reference this hands out is one the arrivals route recognises.
    arrival = await client.post(
        "/api/v1/growth/arrivals",
        json={"partner": "bmj", "visitor_key": "vk_refids", "ref_id": items[0]["ref_id"]},
    )
    assert arrival.json()["exam_code"] == "ortho"


async def test_casc_is_not_offered_as_a_reference(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """CASC is outside the pilot — which is now a flag on the row, not a constant."""
    token = await make_actor("casc@bmj.com")
    await repository.add_reporter(db_session, partner="bmj", email="casc@bmj.com")
    await db_session.flush()

    items = (await client.get("/api/v1/growth/partners/bmj/ref-ids", headers=bearer(token))).json()["items"]
    assert "casc" not in {row["exam_code"] for row in items}


async def test_references_are_refused_to_someone_who_is_not_a_reporter(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("nosy-links@example.com")
    response = await client.get("/api/v1/growth/partners/bmj/ref-ids", headers=bearer(token))
    assert response.status_code == 403
    assert response.json()["code"] == "not_a_partner_reporter"


async def test_references_are_refused_for_an_unknown_partner(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("someone@elsewhere.com")
    response = await client.get("/api/v1/growth/partners/acme/ref-ids", headers=bearer(token))
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_partner"
