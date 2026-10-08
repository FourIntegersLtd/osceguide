"""SAML 2.0 sign-in (E-20), against a real signed response.

The IdP here has its own key and certificate and signs with `python3-saml`'s
signer, so what is proven is the platform's verification of XML-DSig, the
issuer, the audience, the recipient and `InResponseTo` — and that the person
comes out of it provisioned exactly as an OIDC sign-in provisions them.
"""

from __future__ import annotations

import base64
import uuid
from urllib.parse import parse_qs, urlsplit

import jwt
import pytest
from httpx import AsyncClient

from app.core.settings import get_settings
from tests.support.saml_idp import IDP_ENTITY_ID, IDP_SSO_URL, TestIdentityProvider
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def a_saml_org(client: AsyncClient, make_actor, idp: TestIdentityProvider) -> dict:  # type: ignore[no-untyped-def]
    """An organisation that signs in with SAML, and its connection as the console reads it."""
    root = await make_actor("root-saml@osceguide.com", platform_admin=True)
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": "kings", "name": "Kings", "org_type": "institution"},
        headers=bearer(root),
    )
    assert created.status_code == 201, created.text
    connection = await client.put(
        "/api/v1/platform/orgs/kings/sso/saml",
        json={
            "idp_entity_id": IDP_ENTITY_ID,
            "idp_sso_url": IDP_SSO_URL,
            "idp_x509_cert": idp.cert_pem,
            "enabled": True,
        },
        headers=bearer(root),
    )
    assert connection.status_code == 200, connection.text
    sso = await client.put(
        "/api/v1/platform/orgs/kings/sso",
        json={"provider": "saml", "issuer": IDP_ENTITY_ID, "enabled": True, "email_domains": ["kings.ac.uk"]},
        headers=bearer(root),
    )
    assert sso.status_code == 200, sso.text
    return connection.json()


async def start_sign_in(client: AsyncClient) -> tuple[str, str]:
    """Ask for the sign-in URL; answer the RelayState and the AuthnRequest id it is bound to."""
    login = await client.post("/api/v1/auth/sso/login", json={"org_slug": "kings"})
    assert login.status_code == 200, login.text
    url = urlsplit(login.json()["sign_in_url"])
    assert f"{url.scheme}://{url.netloc}{url.path}" == IDP_SSO_URL
    query = parse_qs(url.query)
    assert "SAMLRequest" in query
    relay_state = query["RelayState"][0]
    request_id = jwt.decode(relay_state, options={"verify_signature": False})["nonce"]
    return relay_state, request_id


def handed_back(location: str) -> dict[str, str]:
    url = urlsplit(location)
    assert url.path == "/auth/sso/callback"
    return {key: values[0] for key, values in parse_qs(url.query).items()}


async def test_a_signed_response_signs_the_person_in_and_provisions_them(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    idp = TestIdentityProvider()
    connection = await a_saml_org(client, make_actor, idp)
    assert connection["sp_acs_url"].endswith(f"/api/v1/sso/saml/{connection['id']}/acs")

    metadata = await client.get(f"/api/v1/sso/saml/{connection['id']}/metadata")
    assert metadata.status_code == 200
    assert metadata.headers["content-type"].startswith("application/samlmetadata+xml")
    assert f'entityID="{connection["sp_entity_id"]}"' in metadata.text
    assert connection["sp_acs_url"] in metadata.text

    relay_state, request_id = await start_sign_in(client)
    posted = await client.post(
        f"/api/v1/sso/saml/{connection['id']}/acs",
        data={
            "SAMLResponse": idp.response(
                acs_url=connection["sp_acs_url"],
                audience=connection["sp_entity_id"],
                in_response_to=request_id,
                email="ana.lee@kings.ac.uk",
            ),
            "RelayState": relay_state,
        },
    )
    assert posted.status_code == 303, posted.text
    handoff = handed_back(posted.headers["location"])
    assert handoff["org_slug"] == "kings" and "error" not in handoff
    assert posted.headers["location"].startswith(get_settings().frontend_url)

    signed_in = await client.post(
        "/api/v1/auth/sso/callback", json={"org_slug": "kings", "token": handoff["token"]}
    )
    assert signed_in.status_code == 200, signed_in.text
    me = await client.get("/api/v1/me", headers=bearer(signed_in.json()["access_token"]))
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "ana.lee@kings.ac.uk"
    assert me.json()["name"] == "Ana Lee"


@pytest.mark.parametrize("fault", ["tampered", "other_request", "other_idp", "wrong_audience"])
async def test_a_response_that_fails_any_check_signs_nobody_in(
    client: AsyncClient, make_actor, fault: str
) -> None:  # type: ignore[no-untyped-def]
    idp = TestIdentityProvider()
    connection = await a_saml_org(client, make_actor, idp)
    relay_state, request_id = await start_sign_in(client)

    signer = TestIdentityProvider() if fault == "other_idp" else idp
    saml_response = signer.response(
        acs_url=connection["sp_acs_url"],
        audience="https://someone-else.example.com"
        if fault == "wrong_audience"
        else connection["sp_entity_id"],
        in_response_to=f"_{uuid.uuid4().hex}" if fault == "other_request" else request_id,
        email="ana.lee@kings.ac.uk",
    )
    if fault == "tampered":
        document = base64.b64decode(saml_response).decode()
        saml_response = base64.b64encode(document.replace("ana.lee@", "admin@").encode()).decode()

    posted = await client.post(
        f"/api/v1/sso/saml/{connection['id']}/acs",
        data={"SAMLResponse": saml_response, "RelayState": relay_state},
    )
    assert posted.status_code == 303, posted.text
    handoff = handed_back(posted.headers["location"])
    assert handoff.get("error") == "sso_verification_failed"
    assert "token" not in handoff


async def test_a_handoff_is_not_accepted_for_another_organisation_or_forged(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    idp = TestIdentityProvider()
    await a_saml_org(client, make_actor, idp)
    forged = jwt.encode(
        {"purpose": "saml-assertion", "org_slug": "kings", "sub": "x", "email": "x@x.com"}, "guess"
    )
    refused = await client.post("/api/v1/auth/sso/callback", json={"org_slug": "kings", "token": forged})
    assert refused.status_code == 422
    assert refused.json()["code"] == "sso_verification_failed"


async def test_an_unknown_connection_has_no_metadata(client: AsyncClient) -> None:
    missing = await client.get(f"/api/v1/sso/saml/{uuid.uuid4()}/metadata")
    assert missing.status_code == 404
    assert missing.json()["code"] == "saml_connection_not_found"


async def test_a_certificate_that_is_not_one_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root-cert@osceguide.com", platform_admin=True)
    await client.post(
        "/api/v1/platform/organizations",
        json={"slug": "kings", "name": "Kings", "org_type": "institution"},
        headers=bearer(root),
    )
    refused = await client.put(
        "/api/v1/platform/orgs/kings/sso/saml",
        json={"idp_entity_id": IDP_ENTITY_ID, "idp_sso_url": IDP_SSO_URL, "idp_x509_cert": "AB:CD:EF"},
        headers=bearer(root),
    )
    assert refused.status_code == 422
    assert refused.json()["code"] == "invalid_saml_connection"


class OnceStore:
    """Just enough of Redis for `SET NX`: the single-use check, without a server."""

    def __init__(self) -> None:
        self.keys: set[str] = set()

    async def set(self, key: str, value: str, *, nx: bool, ex: int) -> bool:
        """True the first time a key is set, as Redis answers `SET key value NX`."""
        if key in self.keys:
            return False
        self.keys.add(key)
        return True


async def signed_in_handoff(
    client: AsyncClient, connection: dict, idp: TestIdentityProvider, email: str
) -> str:
    """Post a valid response for `email` to the assertion consumer; answer the hand-off token."""
    relay_state, request_id = await start_sign_in(client)
    posted = await client.post(
        f"/api/v1/sso/saml/{connection['id']}/acs",
        data={
            "SAMLResponse": idp.response(
                acs_url=connection["sp_acs_url"],
                audience=connection["sp_entity_id"],
                in_response_to=request_id,
                email=email,
            ),
            "RelayState": relay_state,
        },
    )
    assert posted.status_code == 303, posted.text
    return handed_back(posted.headers["location"])["token"]


async def test_a_handoff_signs_in_once_and_a_response_is_consumed_once(
    client: AsyncClient, make_actor, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    from app.features.sso import state as sso_state

    store = OnceStore()
    monkeypatch.setattr(sso_state, "get_redis", lambda: store)
    idp = TestIdentityProvider()
    connection = await a_saml_org(client, make_actor, idp)

    relay_state, request_id = await start_sign_in(client)
    form = {
        "SAMLResponse": idp.response(
            acs_url=connection["sp_acs_url"],
            audience=connection["sp_entity_id"],
            in_response_to=request_id,
            email="ana.lee@kings.ac.uk",
        ),
        "RelayState": relay_state,
    }
    first = await client.post(f"/api/v1/sso/saml/{connection['id']}/acs", data=form)
    token = handed_back(first.headers["location"])["token"]
    replayed = await client.post(f"/api/v1/sso/saml/{connection['id']}/acs", data=form)
    assert handed_back(replayed.headers["location"]).get("error") == "sso_verification_failed"

    signed_in = await client.post("/api/v1/auth/sso/callback", json={"org_slug": "kings", "token": token})
    assert signed_in.status_code == 200, signed_in.text
    again = await client.post("/api/v1/auth/sso/callback", json={"org_slug": "kings", "token": token})
    assert again.status_code == 422
    assert again.json()["code"] == "sso_verification_failed"


async def test_the_idp_is_not_believed_for_an_address_outside_the_organisations_domains(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    # A customer's IdP can assert any address. Without this check it could sign
    # itself into another tenant's account, or a platform administrator's.
    await make_actor("root@osceguide.com", platform_admin=True)
    idp = TestIdentityProvider()
    connection = await a_saml_org(client, make_actor, idp)
    token = await signed_in_handoff(client, connection, idp, "root@osceguide.com")

    refused = await client.post("/api/v1/auth/sso/callback", json={"org_slug": "kings", "token": token})
    assert refused.status_code == 422
    assert refused.json()["code"] == "sso_verification_failed"


async def test_saving_a_saml_connection_is_audited_and_needs_https(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    idp = TestIdentityProvider()
    await a_saml_org(client, make_actor, idp)
    root = await make_actor("root-saml-audit@osceguide.com", platform_admin=True)
    body = {"idp_entity_id": IDP_ENTITY_ID, "idp_x509_cert": idp.cert_pem, "enabled": True}

    insecure = await client.put(
        "/api/v1/platform/orgs/kings/sso/saml",
        json={**body, "idp_sso_url": "http://idp.example.com/sso"},
        headers=bearer(root),
    )
    assert insecure.status_code == 422, insecure.text

    audit = await client.get("/api/v1/platform/audit", headers=bearer(root))
    rows = [r for r in audit.json()["items"] if r["action"] == "sso.saml_saved"]
    assert [r["summary"] for r in rows] == ["Saved the SAML connection for kings (enabled)"]
    assert rows[0]["actor_email"] == "root-saml@osceguide.com"
