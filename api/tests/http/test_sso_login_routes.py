"""Signing in through a broker: the login URL, and the callback that mints a session.

The broker is a port, so every test here runs against `FakeSsoBroker` and none
reaches Clerk. What is being proved is the platform's half — that the right
organisation's arrangement drives the flow, that a verified token becomes a
provisioned user and a platform pair, and that an unverified one becomes
nothing.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.ports import SsoIdentity
from app.features.sso.service_login import get_sso_broker
from tests.support.fakes import FakeSsoBroker
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

LOGIN = "/api/v1/auth/sso/login"
CALLBACK = "/api/v1/auth/sso/callback"


async def _org(client: AsyncClient, root: str, slug: str) -> None:
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(root),
    )
    assert created.status_code == 201, created.text


def _config(**over: object) -> dict:
    body: dict = {
        "provider": "clerk",
        "issuer": "bmj.accounts.dev",
        "enabled": True,
        "sso_only": True,
        "sign_in_label": "Sign in with BMJ",
        "hosts": ["bmj.osceguide.com"],
        "email_domains": ["bmj.com"],
    }
    body.update(over)
    return body


async def _enable(client: AsyncClient, root: str, slug: str, **over: object) -> None:
    await _org(client, root, slug)
    saved = await client.put(f"/api/v1/platform/orgs/{slug}/sso", json=_config(**over), headers=bearer(root))
    assert saved.status_code == 200, saved.text


def _use(client: AsyncClient, fake: FakeSsoBroker) -> None:
    client._transport.app.dependency_overrides[get_sso_broker] = lambda: fake  # type: ignore[attr-defined]


async def test_login_returns_the_brokers_sign_in_url(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await _enable(client, root, "bmj")
    fake = FakeSsoBroker()
    _use(client, fake)

    found = await client.post(LOGIN, json={"org_slug": "bmj"})
    assert found.status_code == 200, found.text
    # The organisation's stored issuer drives the URL, and the browser is sent
    # back to a frontend callback page rather than to this API. (The fake does
    # not URL-encode the redirect; the real Clerk adapter does.)
    assert found.json()["sign_in_url"].startswith("https://bmj.accounts.dev/sign-in?redirect_url=")
    assert "/auth/sso/callback" in fake.sign_in_urls[0]
    assert "org_slug=bmj" in fake.sign_in_urls[0]


async def test_a_verified_callback_provisions_the_person_and_mints_a_session(
    client: AsyncClient,
    make_actor,  # type: ignore[no-untyped-def]
) -> None:
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await _enable(client, root, "bmj")
    fake = FakeSsoBroker(identity=SsoIdentity(email="doctor@bmj.com", name="Dr Who", subject="clerk_1"))
    _use(client, fake)

    result = await client.post(CALLBACK, json={"org_slug": "bmj", "token": "clerk-session-token"})
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["access_token"] and body["refresh_token"]
    assert fake.verified == ["clerk-session-token"]

    # The token is a real platform session for a user that did not exist before
    # the callback: it provisions on first sign-in because the institution
    # vouches for them.
    me = await client.get("/api/v1/me", headers=bearer(body["access_token"]))
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "doctor@bmj.com"


async def test_a_second_sign_in_finds_the_same_account(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await _enable(client, root, "bmj")
    fake = FakeSsoBroker(identity=SsoIdentity(email="doctor@bmj.com", name="Dr Who", subject="clerk_1"))
    _use(client, fake)

    first = await client.post(CALLBACK, json={"org_slug": "bmj", "token": "t1"})
    second = await client.post(CALLBACK, json={"org_slug": "bmj", "token": "t2"})
    assert first.status_code == second.status_code == 200

    me = await client.get("/api/v1/me", headers=bearer(second.json()["access_token"]))
    assert me.json()["email"] == "doctor@bmj.com"
    # One person, not two: the second sign-in resolves by the broker's subject
    # and lands on the account the first one created.
    first_me = await client.get("/api/v1/me", headers=bearer(first.json()["access_token"]))
    assert me.json()["id"] == first_me.json()["id"]


async def test_an_unverified_token_becomes_nothing(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await _enable(client, root, "bmj")
    _use(client, FakeSsoBroker(identity=None))  # the broker vouches for nobody

    refused = await client.post(CALLBACK, json={"org_slug": "bmj", "token": "forged"})
    assert refused.status_code == 422, refused.text
    assert refused.json()["code"] == "sso_verification_failed"


async def test_an_organisation_with_no_arrangement_signs_in_here(client: AsyncClient) -> None:
    _use(client, FakeSsoBroker())
    missing = await client.post(LOGIN, json={"org_slug": "nobody"})
    assert missing.status_code == 404
    assert missing.json()["code"] == "sso_not_configured"


async def test_a_provider_with_no_flow_here_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await _enable(
        client,
        root,
        "kings",
        provider="entra",
        issuer="https://login.microsoftonline.com/kings",
        sso_only=False,
    )
    _use(client, FakeSsoBroker())

    refused = await client.post(LOGIN, json={"org_slug": "kings"})
    assert refused.status_code == 503, refused.text
    assert refused.json()["code"] == "sso_provider_unsupported"


async def test_a_broker_that_cannot_be_reached_fails_closed(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await _enable(client, root, "bmj")
    _use(client, FakeSsoBroker(unavailable=True))

    down = await client.post(CALLBACK, json={"org_slug": "bmj", "token": "t"})
    assert down.status_code == 503, down.text
    assert down.json()["code"] == "sso_login_unavailable"
