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
from sqlalchemy.ext.asyncio import AsyncSession

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


async def test_an_entra_organisation_signs_in_through_its_own_flow(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Direct OIDC, dispatched the same way Clerk is — `for_provider` picks
    the adapter, the rest of the flow does not know which one it got."""
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await _enable(
        client,
        root,
        "kings",
        provider="entra",
        issuer="a1b2c3d4-tenant-id",
        sso_only=False,
    )
    fake = FakeSsoBroker(
        identity=SsoIdentity(email="doctor@kings.nhs.uk", name="Dr Who", subject="entra_oid_1")
    )
    _use(client, fake)

    found = await client.post(LOGIN, json={"org_slug": "kings"})
    assert found.status_code == 200, found.text
    # SEC-015: the sign-in request carried a signed state and a nonce.
    state = fake.issued_states[0]
    assert state and fake.issued_nonces[0]

    result = await client.post(CALLBACK, json={"org_slug": "kings", "token": "auth-code", "state": state})
    assert result.status_code == 200, result.text
    # ...and the nonce inside that state is what the broker was told to expect.
    assert fake.expected_nonces == [fake.issued_nonces[0]]
    me = await client.get("/api/v1/me", headers=bearer(result.json()["access_token"]))
    assert me.json()["email"] == "doctor@kings.nhs.uk"


async def test_an_entra_callback_without_a_state_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """SEC-015: the OIDC code flow must carry the signed state its sign-in
    minted. A callback with no state — a forged or replayed one — is refused
    before the broker is ever asked to verify the code."""
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await _enable(client, root, "kings", provider="entra", issuer="a1b2c3d4-tenant-id", sso_only=False)
    fake = FakeSsoBroker(
        identity=SsoIdentity(email="doctor@kings.nhs.uk", name="Dr Who", subject="entra_oid_1")
    )
    _use(client, fake)

    refused = await client.post(CALLBACK, json={"org_slug": "kings", "token": "auth-code"})
    assert refused.status_code == 422, refused.text
    assert refused.json()["code"] == "sso_verification_failed"
    # The code was never presented to the broker: the state failed first.
    assert fake.verified == []


async def test_an_entra_callback_with_a_foreign_state_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """SEC-015: a state minted for one organisation cannot be replayed against
    another. The signed state names its org, and the callback refuses one that
    does not match the org it claims to be for."""
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await _enable(
        client,
        root,
        "kings",
        provider="entra",
        issuer="a1b2c3d4-tenant-id",
        sso_only=False,
        hosts=["kings.osceguide.com"],
        email_domains=["kings.nhs.uk"],
    )
    await _enable(
        client,
        root,
        "guys",
        provider="entra",
        issuer="e5f6-guys-tenant",
        sso_only=False,
        hosts=["guys.osceguide.com"],
        email_domains=["guys.nhs.uk"],
    )
    fake = FakeSsoBroker(
        identity=SsoIdentity(email="doctor@kings.nhs.uk", name="Dr Who", subject="entra_oid_1")
    )
    _use(client, fake)

    # A state legitimately issued for guys...
    await client.post(LOGIN, json={"org_slug": "guys"})
    guys_state = fake.issued_states[-1]
    assert guys_state

    # ...replayed against kings is refused.
    refused = await client.post(
        CALLBACK, json={"org_slug": "kings", "token": "auth-code", "state": guys_state}
    )
    assert refused.status_code == 422, refused.text
    assert refused.json()["code"] == "sso_verification_failed"
    assert fake.verified == []


async def test_an_unrecognised_provider_stored_on_a_row_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Every value the write path accepts is one of the two `Provider` names,
    so this can only happen to a row that predates today's schema — a read
    that finds one must still answer cleanly rather than raising."""
    from app.features.sso.models import OrganizationSso
    from app.features.tenancy import repository as tenancy_repository

    root = await make_actor("root@osceguide.com", platform_admin=True)
    await _org(client, root, "legacy")
    org = await tenancy_repository.organization_by_slug(db_session, "legacy")
    assert org is not None
    db_session.add(OrganizationSso(org_id=org.id, provider="okta", issuer="legacy.okta.com", enabled=True))
    await db_session.flush()
    _use(client, FakeSsoBroker())

    refused = await client.post(LOGIN, json={"org_slug": "legacy"})
    assert refused.status_code == 503, refused.text
    assert refused.json()["code"] == "sso_provider_unsupported"


async def test_a_broker_that_cannot_be_reached_fails_closed(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await _enable(client, root, "bmj")
    _use(client, FakeSsoBroker(unavailable=True))

    down = await client.post(CALLBACK, json={"org_slug": "bmj", "token": "t"})
    assert down.status_code == 503, down.text
    assert down.json()["code"] == "sso_login_unavailable"


async def test_an_sso_only_arrangement_refuses_a_password_login(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The account this callback provisions cannot then sign in with a
    password anybody guesses, resets or is handed — the whole point of
    `sso_only`, made a stated refusal rather than an accident of a missing
    hash."""
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await _enable(client, root, "bmj")  # `_config()` defaults `sso_only: True`
    fake = FakeSsoBroker(identity=SsoIdentity(email="locked@bmj.com", name="Locked Out", subject="c1"))
    _use(client, fake)
    await client.post(CALLBACK, json={"org_slug": "bmj", "token": "t"})

    refused = await client.post(
        "/api/v1/auth/login", json={"email": "locked@bmj.com", "password": "whatever-it-might-be"}
    )
    assert refused.status_code == 401, refused.text
    assert refused.json()["code"] == "password_login_disabled"

    # The forgot-password flow answers the same non-leaking 202 an unknown
    # address gets, and issues no token — it must not become the back door.
    reset = await client.post("/api/v1/auth/password-reset", json={"email": "locked@bmj.com"})
    assert reset.status_code == 202, reset.text


async def test_an_org_without_sso_only_leaves_the_password_form_open(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await _enable(client, root, "guys", sso_only=False)
    fake = FakeSsoBroker(identity=SsoIdentity(email="both-ways@guys.com", name="Either", subject="c2"))
    _use(client, fake)
    await client.post(CALLBACK, json={"org_slug": "guys", "token": "t"})

    reset = await client.post("/api/v1/auth/password-reset", json={"email": "both-ways@guys.com"})
    assert reset.status_code == 202, reset.text
