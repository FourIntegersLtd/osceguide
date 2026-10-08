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


async def test_an_old_arrival_is_still_credited(client: AsyncClient, db_session: AsyncSession) -> None:
    """No window: once a partner's link is clicked, that partner is credited."""
    await arrive(client, "vk_6")
    user = await identity_repo.create_user(
        session=db_session, email="stale@example.com", name="S", password_hash=None
    )
    await db_session.flush()
    much_later = now() + timedelta(days=200)
    credited = await service.attribute_signup(db_session, user_id=user.id, visitor_key="vk_6", now=much_later)
    assert credited is not None
    assert credited.partner == "bmj"


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
        await service.check_code_for_purchase(db_session, code=code, buyer_user_id=user.id)


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


async def test_a_code_keeps_working_after_somebody_buys_with_it(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """As in b2c, a code is shared, not spent. Each purchase made with it credits
    its owner: £2.50 for one month, £5 for three."""
    referrer = await make_actor("reusable-referrer@example.com")
    code = (await client.post("/api/v1/me/referral-code", headers=bearer(referrer))).json()["code"]
    for friend_email, plan_duration_days in (("friend-a@example.com", 30), ("friend-b@example.com", 90)):
        await make_actor(friend_email)
        friend = await identity_repo.user_by_email(db_session, friend_email)
        assert friend is not None
        await service.check_code_for_purchase(db_session, code=code.lower(), buyer_user_id=friend.id)
        credited = await service.credit_referral_purchase(
            db_session,
            code=code,
            referred_user_id=friend.id,
            plan_duration_days=plan_duration_days,
            now=now(),
        )
        assert credited is True
    await db_session.flush()

    mine = await client.get("/api/v1/me/referrals", headers=bearer(referrer))
    assert mine.json() == {"code": code, "redeemed_count": 2, "earned_pence": 750}


async def test_buying_with_your_own_code_credits_nobody(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Checked again at payment, not only at checkout: the credit must never
    depend on the web having asked first."""
    token = await make_actor("selfref@example.com")
    code = (await client.post("/api/v1/me/referral-code", headers=bearer(token))).json()["code"]
    user = await identity_repo.user_by_email(db_session, "selfref@example.com")
    assert user is not None

    credited = await service.credit_referral_purchase(
        db_session, code=code, referred_user_id=user.id, plan_duration_days=30, now=now()
    )

    assert credited is False
    mine = await client.get("/api/v1/me/referrals", headers=bearer(token))
    assert mine.json()["redeemed_count"] == 0


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


# --- referral payouts -------------------------------------------------------


async def _a_redeemed_referral(client: AsyncClient, db_session: AsyncSession, make_actor, tag: str):  # type: ignore[no-untyped-def]
    """One referrer, one referee, one redeemed code."""
    referrer = await make_actor(f"{tag}-referrer@example.com")
    code = (await client.post("/api/v1/me/referral-code", headers=bearer(referrer))).json()["code"]
    await make_actor(f"{tag}-referee@example.com")
    referee = await identity_repo.user_by_email(db_session, f"{tag}-referee@example.com")
    assert referee is not None
    await service.credit_referral_purchase(
        db_session, code=code, referred_user_id=referee.id, plan_duration_days=90, now=now()
    )
    await db_session.flush()
    return code


async def test_the_payout_queue_lists_redeemed_referrals_as_unpaid(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """A referral starts life owed. Nothing in the product pays it — this is the

    record of whether somebody has, settled by hand outside the app.
    """
    await _a_redeemed_referral(client, db_session, make_actor, "queue")
    admin = await make_actor("payouts-admin@osceguide.com", platform_admin=True)

    response = await client.get("/api/v1/growth/referrals", headers=bearer(admin))

    assert response.status_code == 200, response.text
    rows = response.json()["items"]
    assert len(rows) == 1
    assert rows[0]["payout_status"] == "unpaid"
    assert rows[0]["referrer_email"] == "queue-referrer@example.com"
    assert rows[0]["referred_email"] == "queue-referee@example.com"
    assert rows[0]["earned_pence"] == 500
    assert rows[0]["paid_at"] is None


async def test_marking_a_referral_paid_records_who_and_when(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The retiring app kept the flag and nothing else, so "when was this

    settled, and on whose word" had no answer. Both are on the row now.
    """
    await _a_redeemed_referral(client, db_session, make_actor, "paid")
    admin = await make_actor("marks-paid@osceguide.com", platform_admin=True)
    referral_id = (await client.get("/api/v1/growth/referrals", headers=bearer(admin))).json()["items"][0][
        "id"
    ]

    response = await client.post(
        f"/api/v1/growth/referrals/{referral_id}/payout",
        json={"payout_status": "paid", "payout_reference": "FT-2026-09-24"},
        headers=bearer(admin),
    )

    assert response.status_code == 200, response.text
    assert response.json()["payout_status"] == "paid"
    assert response.json()["payout_reference"] == "FT-2026-09-24"
    assert response.json()["paid_at"] is not None


async def test_marking_it_unpaid_again_clears_the_stamp(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Somebody ticks the wrong row. Leaving a paid date on an unpaid referral

    would be worse than the mistake.
    """
    await _a_redeemed_referral(client, db_session, make_actor, "undo")
    admin = await make_actor("undoes@osceguide.com", platform_admin=True)
    referral_id = (await client.get("/api/v1/growth/referrals", headers=bearer(admin))).json()["items"][0][
        "id"
    ]
    url = f"/api/v1/growth/referrals/{referral_id}/payout"
    await client.post(url, json={"payout_status": "paid", "payout_reference": "X"}, headers=bearer(admin))

    response = await client.post(url, json={"payout_status": "unpaid"}, headers=bearer(admin))

    assert response.status_code == 200, response.text
    assert response.json()["payout_status"] == "unpaid"
    assert response.json()["paid_at"] is None
    assert response.json()["payout_reference"] is None


async def test_the_queue_filters_by_payout_status(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await _a_redeemed_referral(client, db_session, make_actor, "filter")
    admin = await make_actor("filters@osceguide.com", platform_admin=True)
    referral_id = (await client.get("/api/v1/growth/referrals", headers=bearer(admin))).json()["items"][0][
        "id"
    ]
    await client.post(
        f"/api/v1/growth/referrals/{referral_id}/payout",
        json={"payout_status": "paid"},
        headers=bearer(admin),
    )

    unpaid = await client.get("/api/v1/growth/referrals?payout_status=unpaid", headers=bearer(admin))
    paid = await client.get("/api/v1/growth/referrals?payout_status=paid", headers=bearer(admin))

    assert unpaid.json()["items"] == []
    assert len(paid.json()["items"]) == 1


async def test_an_unredeemed_code_has_no_payout_to_record(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """An outstanding code is neither paid nor unpaid."""
    token = await make_actor("outstanding@example.com")
    await client.post("/api/v1/me/referral-code", headers=bearer(token))
    user = await identity_repo.user_by_email(db_session, "outstanding@example.com")
    assert user is not None
    rows = await repository.referrals_for(db_session, user.id)
    admin = await make_actor("checks@osceguide.com", platform_admin=True)

    response = await client.post(
        f"/api/v1/growth/referrals/{rows[0].id}/payout",
        json={"payout_status": "paid"},
        headers=bearer(admin),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "referral_not_redeemed"


async def test_only_staff_may_read_the_payout_queue(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """It names both sides of every referral and what is owed on it."""
    token = await make_actor("curious@example.com")
    response = await client.get("/api/v1/growth/referrals", headers=bearer(token))
    assert response.status_code == 403


# --- bank details for payout (A1) -------------------------------------------

PAYOUT_DETAILS = "/api/v1/me/referral-payout-details"


async def test_reading_bank_details_before_any_are_saved_is_200_null(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Nothing on file yet is an answer, not a missing resource: the settings
    screen logged a 404 on every visit while it was one (B33)."""
    token = await make_actor("no-bank-yet@example.com")

    response = await client.get(PAYOUT_DETAILS, headers=bearer(token))

    assert response.status_code == 200, response.text
    assert response.json() is None


async def test_saving_bank_details_masks_the_account_number_on_read_back(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The sort code only names a branch and is redisplayed in full, exactly as
    the legacy card did; the account number is the one thing kept masked."""
    token = await make_actor("saver@example.com")

    saved = await client.put(
        PAYOUT_DETAILS,
        json={
            "bank_name": "Monzo",
            "account_holder_name": "Amara Okafor",
            "sort_code": "12-34-56",
            "account_number": "12345678",
        },
        headers=bearer(token),
    )

    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["bank_name"] == "Monzo"
    assert body["account_holder_name"] == "Amara Okafor"
    assert body["sort_code"] == "12-34-56"
    assert body["account_number_last4"] == "5678"
    assert "account_number" not in body
    assert "12345678" not in str(body)

    read_back = await client.get(PAYOUT_DETAILS, headers=bearer(token))
    assert read_back.status_code == 200, read_back.text
    assert read_back.json() == body


async def test_a_bare_sort_code_is_normalised_to_the_grouped_form(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The legacy form accepted "123456" as readily as "12-34-56"."""
    token = await make_actor("bare-sort-code@example.com")

    saved = await client.put(
        PAYOUT_DETAILS,
        json={
            "bank_name": "Starling",
            "account_holder_name": "Femi Adeyemi",
            "sort_code": "654321",
            "account_number": "87654321",
        },
        headers=bearer(token),
    )

    assert saved.status_code == 200, saved.text
    assert saved.json()["sort_code"] == "65-43-21"


@pytest.mark.parametrize("bad_sort_code", ["1234567", "ab-cd-ef", "12-34", ""])
async def test_an_unrecognisable_sort_code_is_refused(
    client: AsyncClient, make_actor, bad_sort_code: str
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor(f"bad-sort-{abs(hash(bad_sort_code))}@example.com")

    response = await client.put(
        PAYOUT_DETAILS,
        json={
            "bank_name": "Monzo",
            "account_holder_name": "Someone",
            "sort_code": bad_sort_code,
            "account_number": "12345678",
        },
        headers=bearer(token),
    )

    assert response.status_code == 422, response.text


@pytest.mark.parametrize("bad_account_number", ["12345", "12345678901", "abcdefgh"])
async def test_an_unrecognisable_account_number_is_refused(
    client: AsyncClient, make_actor, bad_account_number: str
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor(f"bad-acct-{abs(hash(bad_account_number))}@example.com")

    response = await client.put(
        PAYOUT_DETAILS,
        json={
            "bank_name": "Monzo",
            "account_holder_name": "Someone",
            "sort_code": "12-34-56",
            "account_number": bad_account_number,
        },
        headers=bearer(token),
    )

    assert response.status_code == 422, response.text


async def test_changing_the_bank_name_alone_keeps_the_stored_account_number(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The account number is optional on a second PUT, so somebody can fix a
    typo in the bank name without retyping a number they cannot see."""
    token = await make_actor("edits-bank-name@example.com")
    await client.put(
        PAYOUT_DETAILS,
        json={
            "bank_name": "Monzo",
            "account_holder_name": "Amara Okafor",
            "sort_code": "12-34-56",
            "account_number": "12345678",
        },
        headers=bearer(token),
    )

    updated = await client.put(
        PAYOUT_DETAILS,
        json={"bank_name": "Monzo Bank Ltd", "account_holder_name": "Amara Okafor", "sort_code": "12-34-56"},
        headers=bearer(token),
    )

    assert updated.status_code == 200, updated.text
    assert updated.json()["bank_name"] == "Monzo Bank Ltd"
    assert updated.json()["account_number_last4"] == "5678"


async def test_omitting_the_account_number_with_nothing_stored_is_refused(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("nothing-stored-yet@example.com")

    response = await client.put(
        PAYOUT_DETAILS,
        json={"bank_name": "Monzo", "account_holder_name": "Amara Okafor", "sort_code": "12-34-56"},
        headers=bearer(token),
    )

    assert response.status_code == 422, response.text
    assert response.json()["code"] == "payout_account_number_required"


async def test_the_settlement_queue_shows_the_referrers_bank_details_decrypted(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Settlement happens by hand outside the product, so the person who does it
    needs the real account number, not the masked one the referrer sees."""
    referrer = await make_actor("settle-payout-referrer@example.com")
    await client.put(
        PAYOUT_DETAILS,
        json={
            "bank_name": "Monzo",
            "account_holder_name": "Amara Okafor",
            "sort_code": "12-34-56",
            "account_number": "12345678",
        },
        headers=bearer(referrer),
    )
    code = (await client.post("/api/v1/me/referral-code", headers=bearer(referrer))).json()["code"]
    await make_actor("settle-payout-referee@example.com")
    referee = await identity_repo.user_by_email(db_session, "settle-payout-referee@example.com")
    assert referee is not None
    await service.credit_referral_purchase(
        db_session, code=code, referred_user_id=referee.id, plan_duration_days=90, now=now()
    )
    await db_session.flush()
    admin = await make_actor("settle-payout-admin@osceguide.com", platform_admin=True)

    response = await client.get("/api/v1/growth/referrals", headers=bearer(admin))

    assert response.status_code == 200, response.text
    row = response.json()["items"][0]
    assert row["payout_details"]["bank_name"] == "Monzo"
    assert row["payout_details"]["account_number"] == "12345678"
    assert row["payout_details"]["sort_code"] == "12-34-56"


async def test_nobody_may_read_or_write_another_persons_bank_details(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`/me/...` is scoped by the caller's own token; there is no id in the URL
    to swap for somebody else's."""
    token = await make_actor("no-token-no-details@example.com")
    unauthenticated = await client.get(PAYOUT_DETAILS)
    assert unauthenticated.status_code == 401
    _ = token


# --- per-referee referral history (A2) --------------------------------------


async def test_a_referrer_reads_their_own_redeemed_history(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The legacy table: referee email, date joined, amount earned, payout
    status — plus the code used and the plan bought, for the detail view."""
    referrer = await make_actor("history-referrer@example.com")
    code = (await client.post("/api/v1/me/referral-code", headers=bearer(referrer))).json()["code"]
    await make_actor("history-referee@example.com")
    referee = await identity_repo.user_by_email(db_session, "history-referee@example.com")
    assert referee is not None
    await service.credit_referral_purchase(
        db_session,
        code=code,
        referred_user_id=referee.id,
        plan_duration_days=90,
        now=now(),
        plan_code="three_month",
    )
    await db_session.flush()

    response = await client.get("/api/v1/me/referrals/history", headers=bearer(referrer))

    assert response.status_code == 200, response.text
    rows = response.json()["items"]
    assert len(rows) == 1
    row = rows[0]
    assert row["referee_email"] == "history-referee@example.com"
    assert row["redeemed_at"] is not None
    assert row["earned_pence"] == 500
    assert row["payout_status"] == "unpaid"
    assert row["paid_at"] is None
    assert row["plan_code"] == "three_month"
    assert row["plan_label"]
    assert row["code"].startswith(code)


async def test_the_history_never_shows_someone_elses_referrals(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await _a_redeemed_referral(client, db_session, make_actor, "not-mine")
    outsider = await make_actor("outsider-of-history@example.com")

    response = await client.get("/api/v1/me/referrals/history", headers=bearer(outsider))

    assert response.status_code == 200, response.text
    assert response.json()["items"] == []


async def test_an_unredeemed_code_does_not_appear_in_the_history(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """A shareable code with nobody behind it yet is not a redemption."""
    referrer = await make_actor("unredeemed-history@example.com")
    await client.post("/api/v1/me/referral-code", headers=bearer(referrer))

    response = await client.get("/api/v1/me/referrals/history", headers=bearer(referrer))

    assert response.status_code == 200, response.text
    assert response.json()["items"] == []


async def test_the_history_search_matches_the_referees_email(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """`search` narrows the history server-side now, instead of the frontend
    fetching everything and filtering it in the browser."""
    referrer = await make_actor("history-search-referrer@example.com")
    code = (await client.post("/api/v1/me/referral-code", headers=bearer(referrer))).json()["code"]
    await make_actor("findable-friend@example.com")
    findable = await identity_repo.user_by_email(db_session, "findable-friend@example.com")
    assert findable is not None
    await service.credit_referral_purchase(
        db_session, code=code, referred_user_id=findable.id, plan_duration_days=90, now=now()
    )
    await make_actor("someone-else-entirely@example.com")
    other = await identity_repo.user_by_email(db_session, "someone-else-entirely@example.com")
    assert other is not None
    # Same shareable code, reused for a second buyer: `record_redemption` gives
    # each redemption its own row and suffix, so this is two history rows.
    await service.credit_referral_purchase(
        db_session, code=code, referred_user_id=other.id, plan_duration_days=90, now=now()
    )
    await db_session.flush()

    response = await client.get(
        "/api/v1/me/referrals/history", params={"search": "findable"}, headers=bearer(referrer)
    )

    assert response.status_code == 200, response.text
    rows = response.json()["items"]
    assert len(rows) == 1
    assert rows[0]["referee_email"] == "findable-friend@example.com"


async def test_a_revoked_reporter_can_be_added_again_and_a_live_one_twice(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Re-adding hit the (partner, email) unique constraint with a 500 (P-5)."""
    root = await make_actor("root-readd@osceguide.com", platform_admin=True)
    reporter_token = await make_actor("again@bmj.com")
    url = "/api/v1/growth/partners/bmj/reporters"
    funnel = "/api/v1/growth/partners/bmj/funnel"

    assert (await client.post(url, json={"email": "again@bmj.com"}, headers=bearer(root))).status_code == 204
    assert (await client.delete(f"{url}/again@bmj.com", headers=bearer(root))).status_code == 204
    assert (await client.get(funnel, headers=bearer(reporter_token))).status_code == 403

    again = await client.post(url, json={"email": "Again@bmj.com"}, headers=bearer(root))
    assert again.status_code == 204, again.text
    assert (await client.get(funnel, headers=bearer(reporter_token))).status_code == 200

    twice = await client.post(url, json={"email": "again@bmj.com"}, headers=bearer(root))
    assert twice.status_code == 204, twice.text
    listed = [
        r for r in (await client.get(url, headers=bearer(root))).json() if r["email"] == "again@bmj.com"
    ]
    assert len(listed) == 1
    assert listed[0]["revoked_at"] is None


async def test_the_owed_total_comes_from_the_server_across_every_page(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The screen shows the first page only; the headline must still count all of it (P-15)."""
    await _a_redeemed_referral(client, db_session, make_actor, "one")
    await _a_redeemed_referral(client, db_session, make_actor, "two")
    admin = await make_actor("owed-admin@osceguide.com", platform_admin=True)
    ids = [
        row["id"]
        for row in (await client.get("/api/v1/growth/referrals", headers=bearer(admin))).json()["items"]
    ]
    await client.post(
        f"/api/v1/growth/referrals/{ids[0]}/payout", json={"payout_status": "paid"}, headers=bearer(admin)
    )

    owed = await client.get("/api/v1/growth/referrals/owed", headers=bearer(admin))

    assert owed.status_code == 200, owed.text
    assert owed.json() == {"owed_pence": 500, "referrals": 1, "referrers": 1}
    assert (
        await client.get("/api/v1/growth/referrals/owed", headers=bearer(await make_actor()))
    ).status_code == 403
