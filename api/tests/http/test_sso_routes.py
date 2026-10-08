"""Which organisation a visitor belongs to, before they have proved anything.

Every test here is also a test of what an anonymous caller is told, because the
sign-in read is served without a token and the configuration behind it is not.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.support.tokens import bearer

pytestmark = pytest.mark.db

SIGN_IN = "/api/v1/auth/sso/sign-in"


async def an_org(client: AsyncClient, root: str, slug: str) -> dict:
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(root),
    )
    assert created.status_code == 201, created.text
    return created.json()


def a_config(**over: object) -> dict:
    body: dict = {
        "provider": "clerk",
        "issuer": "https://accounts.bmj.com",
        "enabled": True,
        "sso_only": True,
        "sign_in_label": "Sign in with BMJ",
        "hosts": ["https://BMJ.osceguide.com/"],
        "email_domains": ["someone@bmj.com"],
    }
    body.update(over)
    return body


async def test_a_partner_host_is_a_server_side_fact(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await an_org(client, root, "bmj")

    saved = await client.put("/api/v1/platform/orgs/bmj/sso", json=a_config(), headers=bearer(root))
    assert saved.status_code == 200, saved.text
    # Whatever was typed, what is stored is what a Host header will look like.
    assert {b["value"] for b in saved.json()["bindings"]} == {"bmj.osceguide.com", "bmj.com"}

    # No token: this is what a sign-in page asks before anybody has signed in.
    found = await client.get(SIGN_IN, params={"host": "BMJ.osceguide.com"})
    assert found.status_code == 200, found.text
    body = found.json()
    assert body["org_slug"] == "bmj"
    assert body["sso_only"] is True
    assert body["sign_in_label"] == "Sign in with BMJ"


async def test_an_anonymous_caller_learns_nothing_about_the_arrangement(
    client: AsyncClient,
    make_actor,  # type: ignore[no-untyped-def]
) -> None:
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await an_org(client, root, "bmj")
    await client.put("/api/v1/platform/orgs/bmj/sso", json=a_config(), headers=bearer(root))

    body = (await client.get(SIGN_IN, params={"host": "bmj.osceguide.com"})).json()
    # The issuer and the bindings are configuration, and configuration is for
    # administrators. A button needs neither.
    assert "issuer" not in body
    assert "bindings" not in body


async def test_an_address_finds_its_own_institution(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await an_org(client, root, "bmj")
    await client.put("/api/v1/platform/orgs/bmj/sso", json=a_config(), headers=bearer(root))

    found = await client.get(SIGN_IN, params={"email": "Someone@BMJ.com"})
    assert found.status_code == 200, found.text
    assert found.json()["org_slug"] == "bmj"


async def test_an_ordinary_host_is_told_to_sign_in_here(client: AsyncClient) -> None:
    """No SSO is the common case, not an error: a 200 answering `null`, so
    every visit to `/login` does not log a 404. Everybody else uses a password."""
    missing = await client.get(SIGN_IN, params={"host": "staging.osceguide.com"})
    assert missing.status_code == 200, missing.text
    assert missing.json() is None


async def test_an_address_nobody_claims_is_told_to_sign_in_here(client: AsyncClient) -> None:
    missing = await client.get(SIGN_IN, params={"email": "someone@example.com"})
    assert missing.status_code == 200, missing.text
    assert missing.json() is None


async def test_a_configuration_that_is_switched_off_is_not_advertised(
    client: AsyncClient,
    make_actor,  # type: ignore[no-untyped-def]
) -> None:
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await an_org(client, root, "bmj")
    await client.put(
        "/api/v1/platform/orgs/bmj/sso",
        json=a_config(enabled=False, sso_only=False),
        headers=bearer(root),
    )

    found = await client.get(SIGN_IN, params={"host": "bmj.osceguide.com"})
    assert found.status_code == 200, found.text
    # The same answer as a host nobody ever claimed.
    assert found.json() is None


async def test_restricting_sign_in_to_sso_while_sso_is_off_is_refused(
    client: AsyncClient,
    make_actor,  # type: ignore[no-untyped-def]
) -> None:
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await an_org(client, root, "bmj")

    refused = await client.put(
        "/api/v1/platform/orgs/bmj/sso",
        json=a_config(enabled=False, sso_only=True),
        headers=bearer(root),
    )
    assert refused.status_code == 422, refused.text
    assert refused.json()["code"] == "sso_not_configurable"


async def test_two_organisations_cannot_claim_one_host(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Home-realm discovery must not be a coin toss."""
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await an_org(client, root, "bmj")
    await an_org(client, root, "kings")
    await client.put("/api/v1/platform/orgs/bmj/sso", json=a_config(), headers=bearer(root))

    clash = await client.put(
        "/api/v1/platform/orgs/kings/sso",
        json=a_config(email_domains=[], hosts=["bmj.osceguide.com"]),
        headers=bearer(root),
    )
    assert clash.status_code == 409, clash.text
    assert clash.json()["code"] == "sso_binding_taken"

    # And the host still belongs to the organisation that had it.
    found = await client.get(SIGN_IN, params={"host": "bmj.osceguide.com"})
    assert found.json()["org_slug"] == "bmj"


async def test_saving_again_replaces_the_list_rather_than_adding_to_it(
    client: AsyncClient,
    make_actor,  # type: ignore[no-untyped-def]
) -> None:
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await an_org(client, root, "bmj")
    await client.put("/api/v1/platform/orgs/bmj/sso", json=a_config(), headers=bearer(root))

    await client.put(
        "/api/v1/platform/orgs/bmj/sso",
        json=a_config(hosts=["sso.bmj.com"], email_domains=[]),
        headers=bearer(root),
    )
    assert (await client.get(SIGN_IN, params={"host": "bmj.osceguide.com"})).json() is None
    assert (await client.get(SIGN_IN, params={"host": "sso.bmj.com"})).json()["org_slug"] == "bmj"


async def test_only_a_platform_admin_may_read_or_write_it(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await an_org(client, root, "bmj")
    await client.put("/api/v1/platform/orgs/bmj/sso", json=a_config(), headers=bearer(root))

    ordinary = await make_actor("someone@bmj.com")
    assert (await client.get("/api/v1/platform/orgs/bmj/sso", headers=bearer(ordinary))).status_code == 403
    written = await client.put("/api/v1/platform/orgs/bmj/sso", json=a_config(), headers=bearer(ordinary))
    assert written.status_code == 403
    assert (await client.get("/api/v1/platform/orgs/bmj/sso")).status_code == 401


async def test_asking_with_neither_a_host_nor_an_address_is_a_refusal(client: AsyncClient) -> None:
    empty = await client.get(SIGN_IN)
    assert empty.status_code == 422, empty.text
    assert empty.json()["code"] == "invalid_sso_binding"


async def test_an_organisation_with_no_sso_reads_as_null_and_an_unknown_one_is_a_404(
    client: AsyncClient,
    make_actor,  # type: ignore[no-untyped-def]
) -> None:
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await an_org(client, root, "bmj")

    unconfigured = await client.get("/api/v1/platform/orgs/bmj/sso", headers=bearer(root))
    assert unconfigured.status_code == 200, unconfigured.text
    assert unconfigured.json() is None

    unknown = await client.get("/api/v1/platform/orgs/nope/sso", headers=bearer(root))
    assert unknown.status_code == 404
    assert unknown.json()["code"] == "org_not_found"


async def test_switching_to_sso_only_lists_the_members_who_sign_in_with_a_password(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """P-21: SSO-only hides the password form, so anyone whose only way in is a password is
    locked out. The save is refused with who they are until the admin confirms."""
    from app.features.identity import repository as identity_repo
    from app.features.tenancy import repository as tenancy_repo

    root = await make_actor("root-p21@osceguide.com", platform_admin=True)
    created = await an_org(client, root, "p21")
    seated = await identity_repo.create_user(
        db_session, email="seated@p21.test", name="Seated", password_hash="hash"
    )
    federated = await identity_repo.create_user(
        db_session, email="federated@p21.test", name="Fed", password_hash=None
    )
    for user in (seated, federated):
        await tenancy_repo.add_membership(db_session, org_id=created["id"], user_id=user.id, role="trainee")
    await db_session.commit()

    refused = await client.put("/api/v1/platform/orgs/p21/sso", json=a_config(), headers=bearer(root))
    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "sso_only_password_members"
    assert refused.json()["details"] == {"count": 1, "emails": ["seated@p21.test"]}
    assert (await client.get("/api/v1/platform/orgs/p21/sso", headers=bearer(root))).json() is None

    confirmed = await client.put(
        "/api/v1/platform/orgs/p21/sso",
        json=a_config(confirm_password_members=True),
        headers=bearer(root),
    )
    assert confirmed.status_code == 200, confirmed.text

    # Already SSO-only: saving again is not a new lock-out and asks nothing.
    again = await client.put("/api/v1/platform/orgs/p21/sso", json=a_config(), headers=bearer(root))
    assert again.status_code == 200, again.text
