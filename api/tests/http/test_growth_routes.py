"""Attribution and referrals — where the numbers decide what is owed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.growth import repository, service
from app.features.identity import repository as identity_repo
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


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

    acquired = await service.attribute_signup(db_session, user_id=user.id, visitor_key="vk_4", now=NOW)
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

    first = await service.attribute_signup(db_session, user_id=user.id, visitor_key="vk_5", now=NOW)
    assert first is not None
    second = await service.attribute_signup(db_session, user_id=user.id, visitor_key="vk_5", now=NOW)
    assert second is None


async def test_an_arrival_outside_the_window_is_not_credited(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await arrive(client, "vk_6")
    user = await identity_repo.create_user(
        session=db_session, email="stale@example.com", name="S", password_hash=None
    )
    await db_session.flush()
    much_later = datetime.now(UTC) + timedelta(days=200)
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
    assert await service.attribute_signup(db_session, user_id=user.id, visitor_key=None, now=NOW) is None


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
        await service.redeem_code(db_session, code=code, referred_user_id=user.id, earned_pence=500, now=NOW)
