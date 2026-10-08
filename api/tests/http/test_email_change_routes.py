"""S-23: a person changes their own sign-in address by proving they control the new one."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.models import OutboundMessage
from app.features.roster import repository as roster_repo
from app.features.tenancy import repository as tenancy_repo
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

PASSWORD = "correct horse battery"


async def signed_up(client: AsyncClient, email: str = "old@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "name": "Old Name", "password": PASSWORD}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def queued_token(db_session: AsyncSession, recipient: str) -> str | None:
    rows = list(
        (
            await db_session.execute(
                select(OutboundMessage).where(
                    OutboundMessage.template_key == "email_change", OutboundMessage.recipient == recipient
                )
            )
        ).scalars()
    )
    assert len(rows) <= 1
    return rows[0].payload["token"] if rows else None


async def ask(client: AsyncClient, pair: dict, new_email: str, password: str = PASSWORD):  # type: ignore[no-untyped-def]
    return await client.post(
        "/api/v1/me/email-change",
        json={"new_email": new_email, "current_password": password},
        headers=bearer(pair["access_token"]),
    )


async def test_the_link_sent_to_the_new_address_moves_the_account_and_its_roster_entry(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    pair = await signed_up(client)
    other_device = (
        await client.post("/api/v1/auth/login", json={"email": "old@example.com", "password": PASSWORD})
    ).json()
    org = await tenancy_repo.create_organization(db_session, slug="ec-org", name="EC")
    me = (await client.get("/api/v1/me", headers=bearer(pair["access_token"]))).json()
    trainee = await roster_repo.create_trainee(
        db_session, org.id, email="old@example.com", first_name=None, last_name=None, cohort_id=None
    )
    trainee.user_id = me["id"]
    await db_session.commit()

    asked = await ask(client, pair, "New@Example.com")
    assert asked.status_code == 202, asked.text
    # Nothing changes until the link is used.
    assert (await client.get("/api/v1/me", headers=bearer(pair["access_token"]))).json()["email"] == (
        "old@example.com"
    )
    token = await queued_token(db_session, "new@example.com")
    assert token

    confirmed = await client.post("/api/v1/auth/email-change/confirm", json={"token": token})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json() == {"email": "new@example.com"}

    signed_in = await client.post(
        "/api/v1/auth/login", json={"email": "new@example.com", "password": PASSWORD}
    )
    assert signed_in.status_code == 200, signed_in.text
    old = await client.post("/api/v1/auth/login", json={"email": "old@example.com", "password": PASSWORD})
    assert old.status_code == 401
    # Every earlier session ended: the address is how the account is known.
    refused = await client.post("/api/v1/auth/refresh", json={"refresh_token": other_device["refresh_token"]})
    assert refused.json()["code"] == "invalid_refresh_token"
    await db_session.refresh(trainee)
    assert trainee.email == "new@example.com"
    # The old address is told, in case it was not them.
    told = list(
        (
            await db_session.execute(
                select(OutboundMessage).where(
                    OutboundMessage.template_key == "email_changed_notice",
                    OutboundMessage.recipient == "old@example.com",
                )
            )
        ).scalars()
    )
    assert len(told) == 1


async def test_a_wrong_password_sends_nothing(client: AsyncClient, db_session: AsyncSession) -> None:
    pair = await signed_up(client)
    refused = await ask(client, pair, "new@example.com", password="not the password")
    assert refused.status_code == 401, refused.text
    assert refused.json()["code"] == "invalid_credentials"
    assert await queued_token(db_session, "new@example.com") is None


async def test_an_address_someone_holds_gets_the_same_answer_and_no_email(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Otherwise the form is a way to find out who has an account."""
    pair = await signed_up(client)
    await signed_up(client, "taken@example.com")
    asked = await ask(client, pair, "taken@example.com")
    assert asked.status_code == 202, asked.text
    assert await queued_token(db_session, "taken@example.com") is None


async def test_a_link_for_an_address_taken_in_the_meantime_is_refused(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    pair = await signed_up(client)
    await ask(client, pair, "later@example.com")
    token = await queued_token(db_session, "later@example.com")
    assert token
    await signed_up(client, "later@example.com")

    refused = await client.post("/api/v1/auth/email-change/confirm", json={"token": token})
    assert refused.status_code == 422, refused.text
    assert refused.json()["code"] == "invalid_email_change_token"


async def test_a_link_is_used_once_and_a_forged_one_is_refused(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    pair = await signed_up(client)
    await ask(client, pair, "once@example.com")
    token = await queued_token(db_session, "once@example.com")
    assert token
    assert (await client.post("/api/v1/auth/email-change/confirm", json={"token": token})).status_code == 200

    again = await client.post("/api/v1/auth/email-change/confirm", json={"token": token})
    assert again.json()["code"] == "invalid_email_change_token"
    forged = await client.post("/api/v1/auth/email-change/confirm", json={"token": token[:-3] + "abc"})
    assert forged.json()["code"] == "invalid_email_change_token"


async def test_a_pending_link_dies_when_the_password_is_reset(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A reset is what a person does on suspecting the account; it must void a link already in flight."""
    from app.features.identity import repository as identity_repo
    from app.features.identity.tokens import hash_password

    pair = await signed_up(client)
    await ask(client, pair, "reset@example.com")
    token = await queued_token(db_session, "reset@example.com")
    assert token
    me = (await client.get("/api/v1/me", headers=bearer(pair["access_token"]))).json()
    await identity_repo.set_password_hash(db_session, me["id"], hash_password("a brand new passphrase"))
    await db_session.flush()

    refused = await client.post("/api/v1/auth/email-change/confirm", json={"token": token})
    assert refused.json()["code"] == "invalid_email_change_token"


async def test_asking_for_a_change_warns_the_current_address(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    pair = await signed_up(client)
    await ask(client, pair, "warned@example.com")
    told = list(
        (
            await db_session.execute(
                select(OutboundMessage).where(
                    OutboundMessage.template_key == "email_change_requested",
                    OutboundMessage.recipient == "old@example.com",
                )
            )
        ).scalars()
    )
    assert len(told) == 1
    assert told[0].payload == {"new_email": "warned@example.com"}
