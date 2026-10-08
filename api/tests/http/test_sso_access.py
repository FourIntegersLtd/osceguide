"""Who may configure or read single sign-on, and what each route refuses with.

The sign-in lookup, the broker flow and SAML are in `test_sso_routes`, `test_sso_login_routes`
and `test_saml_routes`. Here: every route against every kind of caller, the not-found codes,
and the bodies a route refuses before it reaches the service.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.support.roles import assert_unauthenticated, callers, refused
from tests.support.sso import a_config

pytestmark = pytest.mark.db

NOBODY = uuid.UUID(int=1)
SAML = {
    "idp_entity_id": "https://idp.example.com/entity",
    "idp_sso_url": "https://idp.example.com/sso",
    "idp_x509_cert": "not a certificate",
}

PLATFORM_ROUTES = [
    ("GET", "/api/v1/platform/orgs/kings/sso", None),
    ("PUT", "/api/v1/platform/orgs/kings/sso", a_config()),
    ("GET", "/api/v1/platform/orgs/kings/sso/saml", None),
    ("PUT", "/api/v1/platform/orgs/kings/sso/saml", SAML),
]


async def test_the_platform_sso_routes_refuse_anonymous_and_every_org_role(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor)
    for method, path, body in PLATFORM_ROUTES:
        await assert_unauthenticated(client, method, path, body)
        for role in ("stranger", "trainee", "supervisor", "partner_admin", "owner"):
            await refused(client, who[role], method, path, body)


@pytest.mark.parametrize("method,path,body", PLATFORM_ROUTES)
async def test_the_platform_sso_routes_say_org_not_found_for_an_unknown_organisation(
    client: AsyncClient, make_actor, method: str, path: str, body
) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor)
    response = await client.request(
        method, path.replace("/kings/", "/nowhere/"), json=body, headers=who["platform"]
    )
    assert response.status_code == 404, response.text
    assert response.json()["code"] in ("org_not_found", "sso_not_configured"), response.text


async def test_saml_has_no_connection_to_read_before_one_is_saved(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    platform = (await callers(client, make_actor))["platform"]
    read = await client.get("/api/v1/platform/orgs/kings/sso/saml", headers=platform)
    assert (read.status_code, read.json()["code"]) == (404, "saml_connection_not_found")
    write = await client.put("/api/v1/platform/orgs/kings/sso/saml", json=SAML, headers=platform)
    # The certificate is checked before the organisation is, so a junk one is the first refusal.
    assert (write.status_code, write.json()["code"]) == (422, "invalid_saml_connection")


@pytest.mark.parametrize(
    "body",
    [
        {"idp_entity_id": "e", "idp_sso_url": "http://insecure.example.com", "idp_x509_cert": "c"},
        {"idp_entity_id": "e", "idp_sso_url": "https://a.example.com", "idp_x509_cert": " "},
    ],
)
async def test_a_saml_connection_must_be_https_and_carry_a_certificate(
    client: AsyncClient, make_actor, body: dict
) -> None:  # type: ignore[no-untyped-def]
    platform = (await callers(client, make_actor))["platform"]
    response = await client.put("/api/v1/platform/orgs/kings/sso/saml", json=body, headers=platform)
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    "role,status",
    [
        ("owner", 200),
        ("partner_admin", 200),
        ("supervisor", 403),
        ("trainee", 403),
        ("stranger", 403),
        ("platform", 403),
    ],
)
async def test_an_org_admin_reads_the_sso_status_and_no_one_else_does(
    client: AsyncClient, make_actor, role: str, status: int
) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor)
    response = await client.get("/api/v1/orgs/kings/sso-status", headers=who[role])
    assert response.status_code == status, response.text
    if status == 200:
        assert response.json() == {
            "configured": False,
            "enabled": False,
            "sso_only": False,
            "sign_in_label": None,
        }


async def test_the_sso_status_needs_a_token(client: AsyncClient) -> None:
    await assert_unauthenticated(client, "GET", "/api/v1/orgs/kings/sso-status")


async def test_a_callback_for_an_organisation_with_no_arrangement_is_sso_not_configured(
    client: AsyncClient,
) -> None:
    response = await client.post("/api/v1/auth/sso/callback", json={"org_slug": "nobody", "token": "t"})
    assert (response.status_code, response.json()["code"]) == (404, "sso_not_configured")


async def test_the_sign_in_lookup_refuses_a_host_and_an_address_together_only_when_neither_resolves(
    client: AsyncClient,
) -> None:
    both = await client.get("/api/v1/auth/sso/sign-in", params={"host": "a.example.com", "email": "a@b.com"})
    assert both.status_code == 200, both.text
    assert both.json() is None


async def test_an_unknown_saml_connection_has_no_acs(client: AsyncClient) -> None:
    form = {"SAMLResponse": "x", "RelayState": "y"}
    response = await client.post(f"/api/v1/sso/saml/{NOBODY}/acs", data=form)
    assert (response.status_code, response.json()["code"]) == (404, "saml_connection_not_found")


async def test_the_acs_refuses_a_form_overflowing_its_size_cap(client: AsyncClient) -> None:
    form = {"SAMLResponse": "x" * 200_001, "RelayState": "y"}
    response = await client.post(f"/api/v1/sso/saml/{NOBODY}/acs", data=form)
    assert response.status_code == 422, response.text


async def test_a_configured_organisations_saml_connection_is_404_until_one_is_saved(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    platform = (await callers(client, make_actor))["platform"]
    saved = await client.put(
        "/api/v1/platform/orgs/kings/sso", json=a_config(provider="saml", sso_only=False), headers=platform
    )
    assert saved.status_code == 200, saved.text
    read = await client.get("/api/v1/platform/orgs/kings/sso/saml", headers=platform)
    assert (read.status_code, read.json()["code"]) == (404, "saml_connection_not_found")
    write = await client.put("/api/v1/platform/orgs/kings/sso/saml", json=SAML, headers=platform)
    assert (write.status_code, write.json()["code"]) == (422, "invalid_saml_connection")
