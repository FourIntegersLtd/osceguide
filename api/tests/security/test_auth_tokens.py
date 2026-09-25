"""Token-forgery and token-type checks (security regression).

These assert the *negative* space of authentication: that a token the server
did not issue, or issued for a different purpose, is refused. They are positive
controls — they should pass on the current code — so that a future change which
weakens `decode_access_token` is caught here rather than in production.

Written for the 2026-09 internal security assessment.
"""

from __future__ import annotations

import time
import uuid

import jwt
import pytest
from httpx import AsyncClient

from app.core.settings import get_settings
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

ME = "/api/v1/me"


def _claims(**overrides: object) -> dict[str, object]:
    now = int(time.time())
    base: dict[str, object] = {
        "iss": get_settings().jwt_issuer,
        "sub": str(uuid.uuid4()),
        "typ": "access",
        "iat": now,
        "exp": now + 900,
        "email": "forged@example.com",
        "memberships": [],
        "active_org": None,
        "platform_admin": True,  # the interesting claim to forge
        "must_change_password": False,
    }
    base.update(overrides)
    return base


async def test_token_signed_with_wrong_secret_is_refused(client: AsyncClient) -> None:
    token = jwt.encode(_claims(), "not-the-real-secret", algorithm="HS256")
    response = await client.get(ME, headers=bearer(token))
    assert response.status_code == 401, response.text


async def test_alg_none_token_is_refused(client: AsyncClient) -> None:
    """An unsigned `alg: none` token must not be accepted as a signed one."""
    token = jwt.encode(_claims(), key="", algorithm="none")
    response = await client.get(ME, headers=bearer(token))
    assert response.status_code == 401, response.text


async def test_expired_token_is_refused(client: AsyncClient) -> None:
    now = int(time.time())
    token = jwt.encode(
        _claims(iat=now - 3600, exp=now - 1800),
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    response = await client.get(ME, headers=bearer(token))
    assert response.status_code == 401, response.text


async def test_wrong_issuer_is_refused(client: AsyncClient) -> None:
    token = jwt.encode(_claims(iss="some-other-issuer"), get_settings().jwt_secret, algorithm="HS256")
    response = await client.get(ME, headers=bearer(token))
    assert response.status_code == 401, response.text


async def test_non_access_token_type_is_refused(client: AsyncClient) -> None:
    """A refresh token (or any non-`access` typ) must not open an access route."""
    token = jwt.encode(_claims(typ="refresh"), get_settings().jwt_secret, algorithm="HS256")
    response = await client.get(ME, headers=bearer(token))
    assert response.status_code == 401, response.text
