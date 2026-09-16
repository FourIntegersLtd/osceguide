"""The identity contract: status codes and error codes, not messages.

The frontend switches on `code`. b2b's client flattens errors to a bare string
and then matches English prose to decide whether to retry — these tests exist
so the replacement never needs to.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.db

REGISTER = {"email": "new@example.com", "name": "New Person", "password": "correct horse battery"}


async def register(client: AsyncClient, **overrides: object) -> object:
    return await client.post("/api/v1/auth/register", json={**REGISTER, **overrides})


async def test_registering_returns_the_user_and_a_token_pair(client: AsyncClient) -> None:
    response = await register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "new@example.com"
    assert body["access_token"] and body["refresh_token"]
    # The secret itself and its hash, not the substring: `must_change_password`
    # is a legitimate field whose name contains "password".
    assert REGISTER["password"] not in str(body)
    assert "password_hash" not in str(body)


async def test_registering_twice_is_a_conflict(client: AsyncClient) -> None:
    await register(client)
    response = await register(client, name="Impostor")
    assert response.status_code == 409
    assert response.json()["code"] == "email_taken"


async def test_the_same_address_in_another_casing_is_the_same_person(client: AsyncClient) -> None:
    await register(client)
    response = await register(client, email="NEW@Example.com")
    assert response.status_code == 409
    assert response.json()["code"] == "email_taken"


async def test_a_weak_password_is_refused_with_a_reason(client: AsyncClient) -> None:
    response = await register(client, password="short")
    assert response.status_code == 422
    assert response.json()["code"] == "weak_password"


async def test_signing_in_returns_a_token_pair(client: AsyncClient) -> None:
    await register(client)
    response = await client.post(
        "/api/v1/auth/login", json={"email": "new@example.com", "password": REGISTER["password"]}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_a_wrong_password_is_refused_without_saying_which_part_was_wrong(
    client: AsyncClient,
) -> None:
    await register(client)
    response = await client.post(
        "/api/v1/auth/login", json={"email": "new@example.com", "password": "wrong password here"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


async def test_an_unknown_address_gives_the_same_answer_as_a_wrong_password(
    client: AsyncClient,
) -> None:
    """Different codes here would turn login into an account-enumeration oracle."""
    response = await client.post(
        "/api/v1/auth/login", json={"email": "ghost@example.com", "password": "whatever it is"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


async def test_a_refresh_token_can_be_exchanged(client: AsyncClient) -> None:
    refresh = (await register(client)).json()["refresh_token"]
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    assert response.json()["refresh_token"] != refresh, "the refresh token must rotate"


async def test_reusing_a_rotated_refresh_token_kills_the_session(client: AsyncClient) -> None:
    """Reuse means it leaked, so the chain dies and the freshly rotated token
    the thief might hold dies with it."""
    first = (await register(client)).json()["refresh_token"]
    second = (await client.post("/api/v1/auth/refresh", json={"refresh_token": first})).json()[
        "refresh_token"
    ]

    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert replay.status_code == 401
    assert replay.json()["code"] == "invalid_refresh_token"

    after = await client.post("/api/v1/auth/refresh", json={"refresh_token": second})
    assert after.status_code == 401, "the whole chain should be revoked, not just the replayed token"


async def test_logging_out_stops_the_refresh_token(client: AsyncClient) -> None:
    body = (await register(client)).json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    assert (await client.post("/api/v1/auth/logout", headers=headers)).status_code == 204
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert response.status_code == 401


async def test_me_returns_the_caller(client: AsyncClient) -> None:
    token = (await register(client)).json()["access_token"]
    response = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "new@example.com"
    assert response.json()["memberships"] == []


async def test_me_without_a_token_is_unauthenticated(client: AsyncClient) -> None:
    response = await client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


async def test_password_reset_never_reveals_whether_an_address_exists(client: AsyncClient) -> None:
    await register(client)
    known = await client.post("/api/v1/auth/password-reset", json={"email": "new@example.com"})
    unknown = await client.post("/api/v1/auth/password-reset", json={"email": "ghost@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()


async def test_a_password_reset_queues_its_email(client: AsyncClient, db_session) -> None:  # type: ignore[no-untyped-def]
    """Queued in the same transaction as the token that makes it valid, so a
    reset that rolled back cannot leave an email promising one."""
    from sqlalchemy import select

    from app.features.notifications.models import OutboundMessage

    await register(client)
    await client.post("/api/v1/auth/password-reset", json={"email": "new@example.com"})

    queued = list(
        (
            await db_session.execute(
                select(OutboundMessage).where(OutboundMessage.template_key == "password_reset")
            )
        ).scalars()
    )
    assert len(queued) == 1
    assert queued[0].recipient == "new@example.com"


async def test_an_unknown_address_queues_nothing(client: AsyncClient, db_session) -> None:  # type: ignore[no-untyped-def]
    """Same 202 either way, but no email to an address we do not hold."""
    from sqlalchemy import select

    from app.features.notifications.models import OutboundMessage

    await client.post("/api/v1/auth/password-reset", json={"email": "ghost@example.com"})
    queued = list((await db_session.execute(select(OutboundMessage))).scalars())
    assert queued == []
