"""SAML 2.0 for one organisation's identity provider, through `python3-saml` (E-20).

The XML signature is checked by the library, never by hand: a hand-rolled check
is how signature-wrapping attacks get in. Everything here is stateless — the
platform keeps nothing between sending a browser to the IdP and the IdP posting
it back (ADR 0004) — so the AuthnRequest's id rides in the signed `state` the
login mints, and is required back as the response's `InResponseTo`.

Attribute mapping mirrors `entra.py`'s claims: an address and a stable
subject are required, a name is best-effort.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from urllib.parse import urlsplit

from onelogin.saml2.authn_request import OneLogin_Saml2_Authn_Request
from onelogin.saml2.response import OneLogin_Saml2_Response
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from app.core.logging import get_logger
from app.core.ports import SsoIdentity

log = get_logger(__name__)

HTTP_POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
HTTP_REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
NAMEID_UNSPECIFIED = "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"


@dataclass(frozen=True)
class ServiceProvider:
    """This platform as one connection's service provider: the two URLs an IdP is given."""

    entity_id: str
    acs_url: str


@dataclass(frozen=True)
class IdentityProvider:
    """One organisation's IdP, as its connection row describes it."""

    entity_id: str
    sso_url: str
    x509_cert: str
    email_attribute: str
    first_name_attribute: str | None = None
    last_name_attribute: str | None = None
    display_name_attribute: str | None = None


def service_provider(public_api_url: str, connection_path: str) -> ServiceProvider:
    """The SP entity id (its metadata URL, by convention) and assertion consumer URL."""
    base = f"{public_api_url.rstrip('/')}{connection_path}"
    return ServiceProvider(entity_id=f"{base}/metadata", acs_url=f"{base}/acs")


def _settings(ours: ServiceProvider, idp: IdentityProvider | None) -> OneLogin_Saml2_Settings:
    """The library's settings for one connection, strict throughout.

    No flag asks for a particular signature: in strict mode the library refuses
    a response in which neither the message nor the assertion is signed by the
    IdP's certificate, which is the requirement.
    """
    return OneLogin_Saml2_Settings(
        {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": ours.entity_id,
                "assertionConsumerService": {"url": ours.acs_url, "binding": HTTP_POST},
                "NameIDFormat": NAMEID_UNSPECIFIED,
            },
            "idp": {
                "entityId": idp.entity_id if idp else "",
                "singleSignOnService": {"url": idp.sso_url if idp else "", "binding": HTTP_REDIRECT},
                "x509cert": _bare_cert(idp.x509_cert) if idp else "",
            },
            "security": {
                "authnRequestsSigned": False,
                "wantAssertionsSigned": False,
                "wantMessagesSigned": False,
                "wantNameId": True,
                "requestedAuthnContext": False,
                "rejectUnsolicitedResponsesWithInResponseTo": True,
            },
        },
        sp_validation_only=idp is None,
    )


def metadata_xml(ours: ServiceProvider) -> str:
    """The SP metadata an institution uploads to its IdP."""
    saml_settings = _settings(ours, None)
    metadata = saml_settings.get_sp_metadata()
    return metadata.decode() if isinstance(metadata, bytes) else str(metadata)


def authn_request(ours: ServiceProvider, idp: IdentityProvider) -> tuple[str, str]:
    """A new AuthnRequest's id, and the encoded request to send by redirect."""
    request = OneLogin_Saml2_Authn_Request(_settings(ours, idp))
    return str(request.get_id()), str(request.get_request())


def sign_in_url(idp: IdentityProvider, *, saml_request: str, relay_state: str) -> str:
    """The IdP's sign-in URL, with the request and the signed state on it (HTTP-Redirect binding)."""
    return str(
        OneLogin_Saml2_Utils.redirect(
            idp.sso_url, {"SAMLRequest": saml_request, "RelayState": relay_state}, True
        )
    )


def verify_response(
    ours: ServiceProvider, idp: IdentityProvider, *, saml_response: str, request_id: str
) -> SsoIdentity | None:
    """The person a posted SAMLResponse vouches for, or None.

    Valid means: signed with this IdP's certificate, issued by this IdP, for
    this SP's audience and assertion consumer URL, within its time window, and
    in response to the AuthnRequest this sign-in sent (`request_id`).
    """
    saml_settings = _settings(ours, idp)
    acs = urlsplit(ours.acs_url)
    request_data = {
        "https": "on" if acs.scheme == "https" else "off",
        "http_host": acs.netloc,
        "script_name": acs.path,
        "get_data": {},
        "post_data": {"SAMLResponse": saml_response},
    }
    try:
        response = OneLogin_Saml2_Response(saml_settings, saml_response)
        if not response.is_valid(request_data, request_id=request_id):
            log.warning("saml response refused", reason=response.get_error())
            return None
        attributes = response.get_attributes()
        subject = str(response.get_nameid() or "")
    except Exception as exc:  # noqa: BLE001 - the library raises many types for a malformed document
        log.warning("saml response could not be read", error=str(exc))
        return None
    email = _first(attributes, idp.email_attribute) or (subject if "@" in subject else "")
    if not email or not subject:
        return None
    name = _first(attributes, idp.display_name_attribute) or " ".join(
        part
        for part in (
            _first(attributes, idp.first_name_attribute),
            _first(attributes, idp.last_name_attribute),
        )
        if part
    )
    return SsoIdentity(email=email.strip(), name=name.strip(), subject=subject)


def _first(attributes: dict[str, list[str]], name: str | None) -> str:
    """The first value of one attribute, or an empty string."""
    if not name:
        return ""
    values = attributes.get(name) or []
    return str(values[0]) if values else ""


def _bare_cert(certificate: str) -> str:
    """The base64 body of a PEM certificate, however it was pasted."""
    lines = [
        line.strip()
        for line in certificate.strip().splitlines()
        if line.strip() and not line.strip().startswith("-----")
    ]
    return "".join(lines)


def is_certificate(certificate: str) -> bool:
    """Whether this parses as base64 at all, so a save refuses a pasted fingerprint."""
    try:
        return len(base64.b64decode(_bare_cert(certificate), validate=True)) > 100
    except ValueError:
        return False
