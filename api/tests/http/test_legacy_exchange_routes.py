"""The legacy login bridge, over real routes.

No password came across in the migration, so without this route the cutover
means a password reset for every live user on the same weekend. These tests
pin the two properties that make the bridge safe to run beside two live
backends: it verifies before it mints, and it creates nobody.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.settings import get_settings
from app.main import create_app

pytestmark = pytest.mark.db

EXCHANGE = "/api/v1/auth/exchange-legacy"
REGISTER = {"email": "doctor@example.com", "name": "A Doctor", "password": "correct horse battery"}

CONSUMER_SECRET = "legacy-consumer-test-secret"  # noqa: S105 - matches tests/conftest.py
INSTITUTION_SECRET = "legacy-institution-test-secret"  # noqa: S105


def legacy_token(
    *,
    secret: str,
    email: str | None = "doctor@example.com",
    expires_in: timedelta = timedelta(days=30),
    token_type: str | None = "access",  # noqa: S107 - a JWT claim value, not a password
    subject: str = "legacy-subject-id",
    **extra: Any,
) -> str:
    """A token shaped the way the legacy backend actually issues one.

    b2c goes through flask-jwt-extended, so `type` is present and the custom
    claims sit at the top level; b2b spreads its claims into the payload and
    sets no `type`. Both sign HS256 and set neither `iss` nor `aud`.
    """
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_in).timestamp()),
        "jti": "legacy-jti",
        **extra,
    }
    if email is not None:
        claims["email"] = email
    if token_type is not None:
        claims["type"] = token_type
    return jwt.encode(claims, secret, algorithm="HS256")


async def register(client: AsyncClient, **overrides: object) -> None:
    response = await client.post("/api/v1/auth/register", json={**REGISTER, **overrides})
    assert response.status_code == 201


async def test_a_consumer_token_buys_a_platform_session(client: AsyncClient) -> None:
    await register(client)
    response = await client.post(
        EXCHANGE, json={"provider": "consumer", "token": legacy_token(secret=CONSUMER_SECRET)}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["email"] == "doctor@example.com"


async def test_an_institution_token_buys_a_platform_session(client: AsyncClient) -> None:
    await register(client)
    # The institution backend sets no `type` claim at all, so requiring one would refuse every
    # real institution token.
    token = legacy_token(secret=INSTITUTION_SECRET, token_type=None)
    response = await client.post(EXCHANGE, json={"provider": "institution", "token": token})
    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_the_exchanged_token_works_on_an_authenticated_route(client: AsyncClient) -> None:
    await register(client)
    exchanged = await client.post(
        EXCHANGE, json={"provider": "consumer", "token": legacy_token(secret=CONSUMER_SECRET)}
    )
    access = exchanged.json()["access_token"]
    me = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["email"] == "doctor@example.com"


async def test_the_address_is_matched_the_way_the_migration_merged_it(client: AsyncClient) -> None:
    await register(client)
    token = legacy_token(secret=CONSUMER_SECRET, email="Doctor@Example.COM")
    response = await client.post(EXCHANGE, json={"provider": "consumer", "token": token})
    assert response.status_code == 200


async def test_a_token_signed_with_the_wrong_secret_is_refused(client: AsyncClient) -> None:
    await register(client)
    response = await client.post(
        EXCHANGE, json={"provider": "consumer", "token": legacy_token(secret="not-the-secret")}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_legacy_token"


async def test_one_arms_secret_does_not_verify_the_others_token(client: AsyncClient) -> None:
    # The provider selects the key. Were either secret tried in turn, leaking
    # one would forge tokens for both arms.
    await register(client)
    response = await client.post(
        EXCHANGE, json={"provider": "consumer", "token": legacy_token(secret=INSTITUTION_SECRET)}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_legacy_token"


async def test_an_expired_legacy_token_is_refused(client: AsyncClient) -> None:
    await register(client)
    stale = legacy_token(secret=CONSUMER_SECRET, expires_in=timedelta(days=-1))
    response = await client.post(EXCHANGE, json={"provider": "consumer", "token": stale})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_legacy_token"


async def test_a_consumer_refresh_token_does_not_buy_a_session(client: AsyncClient) -> None:
    # The consumer backend signs its refresh tokens with the same secret; `type` is the only
    # thing telling them apart, so without that check a stolen refresh token
    # would be as good as an access token here.
    await register(client)
    refresh = legacy_token(secret=CONSUMER_SECRET, token_type="refresh")
    response = await client.post(EXCHANGE, json={"provider": "consumer", "token": refresh})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_legacy_token"


async def test_a_token_with_no_address_is_refused(client: AsyncClient) -> None:
    await register(client)
    response = await client.post(
        EXCHANGE, json={"provider": "consumer", "token": legacy_token(secret=CONSUMER_SECRET, email=None)}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_legacy_token"


async def test_an_address_that_was_never_imported_creates_nobody(client: AsyncClient) -> None:
    token = legacy_token(secret=CONSUMER_SECRET, email="never-imported@example.com")
    response = await client.post(EXCHANGE, json={"provider": "consumer", "token": token})
    assert response.status_code == 401
    assert response.json()["code"] == "legacy_account_not_imported"

    # And the refusal really did not create the account on the way past.
    again = await client.post(EXCHANGE, json={"provider": "consumer", "token": token})
    assert again.json()["code"] == "legacy_account_not_imported"


async def test_an_unknown_provider_is_rejected_by_the_schema(client: AsyncClient) -> None:
    response = await client.post(
        EXCHANGE, json={"provider": "acme", "token": legacy_token(secret=CONSUMER_SECRET)}
    )
    assert response.status_code == 422


async def test_the_legacy_token_cannot_widen_access(client: AsyncClient) -> None:
    # Whatever a thirty-day-old token claims about roles and paid status is
    # ignored: memberships and admin come from this database.
    await register(client)
    token = legacy_token(
        secret=CONSUMER_SECRET,
        role="admin",
        has_paid=True,
        orgSlugs=["some-institution"],
    )
    response = await client.post(EXCHANGE, json={"provider": "consumer", "token": token})
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["is_platform_admin"] is False
    assert body["user"]["memberships"] == []


async def test_an_unconfigured_arm_refuses_rather_than_trusting_the_token() -> None:
    """Fails closed, like the worker guard.

    Built on its own app so the override is real configuration rather than a
    patched attribute: an empty secret must refuse every exchange, not skip
    verification.
    """
    get_settings.cache_clear()
    previous = os.environ.get("LEGACY_CONSUMER_JWT_SECRET")
    os.environ["LEGACY_CONSUMER_JWT_SECRET"] = ""
    try:
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as unconfigured:
            response = await unconfigured.post(
                EXCHANGE, json={"provider": "consumer", "token": legacy_token(secret=CONSUMER_SECRET)}
            )
        assert response.status_code == 503
        assert response.json()["code"] == "legacy_exchange_unavailable"
    finally:
        if previous is None:
            os.environ.pop("LEGACY_CONSUMER_JWT_SECRET", None)
        else:
            os.environ["LEGACY_CONSUMER_JWT_SECRET"] = previous
        get_settings.cache_clear()
