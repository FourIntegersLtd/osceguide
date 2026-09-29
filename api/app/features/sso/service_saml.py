"""SAML 2.0 sign-in for an organisation whose identity provider speaks SAML (E-20).

`service_login` runs every provider's login; for SAML it asks this module for
the sign-in URL, and for the identity behind the token the frontend posts back.
The assertion consumer (`consume_response`) is SAML's own: the IdP posts the
signed response here, the library verifies it, and the browser is handed to
the frontend callback page with a short-lived signed statement of who that was
(`state.issue_assertion`). Provisioning and the session happen where every
other provider's do, in `service_login.complete_callback`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from urllib.parse import urlencode

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import SsoIdentity
from app.core.settings import Settings
from app.features.sso import errors, repository, saml, schemas
from app.features.sso import state as sso_state
from app.features.sso.models import OrganizationSamlConnection
from app.features.tenancy import service as tenancy

# Where the connection's two URLs live under the public API address.
CONNECTION_PATH = "/api/v1/sso/saml/{connection_id}"


def _our_side(settings: Settings, connection_id: uuid.UUID) -> saml.ServiceProvider:
    """This platform as the service provider for one connection."""
    return saml.service_provider(settings.public_api_url, CONNECTION_PATH.format(connection_id=connection_id))


def _idp(connection: OrganizationSamlConnection) -> saml.IdentityProvider:
    """The connection row as the SAML adapter reads it."""
    return saml.IdentityProvider(
        entity_id=connection.idp_entity_id,
        sso_url=connection.idp_sso_url,
        x509_cert=connection.idp_x509_cert,
        email_attribute=connection.email_attribute,
        first_name_attribute=connection.first_name_attribute,
        last_name_attribute=connection.last_name_attribute,
        display_name_attribute=connection.display_name_attribute,
    )


async def metadata(session: AsyncSession, connection_id: uuid.UUID, *, settings: Settings) -> str:
    """The SP metadata an institution uploads to its IdP. Public: it holds nothing secret."""
    connection = await repository.saml_connection_by_id(session, connection_id)
    if connection is None:
        raise errors.SamlConnectionNotFound()
    return saml.metadata_xml(_our_side(settings, connection.id))


async def sign_in_url(
    session: AsyncSession, org_id: uuid.UUID, org_slug: str, *, settings: Settings, now: datetime
) -> str:
    """Where to send the browser: the IdP, with a fresh AuthnRequest and a signed state.

    The request's id is the state's nonce, so the response must answer this
    very request (`InResponseTo`), and a response to anybody else's is refused.
    """
    connection = await _enabled_connection(session, org_id)
    ours = _our_side(settings, connection.id)
    idp = _idp(connection)
    request_id, saml_request = saml.authn_request(ours, idp)
    relay_state, _ = sso_state.issue_state(settings, org_slug=org_slug, now=now, nonce=request_id)
    return saml.sign_in_url(idp, saml_request=saml_request, relay_state=relay_state)


async def consume_response(
    session: AsyncSession,
    connection_id: uuid.UUID,
    *,
    saml_response: str,
    relay_state: str,
    settings: Settings,
    now: datetime,
) -> str:
    """Verify the IdP's posted response; answer the frontend URL to send the browser to.

    A response that fails any check sends the browser to the same page with
    `error=sso_verification_failed` instead, since a person is looking at it.
    """
    connection = await repository.saml_connection_by_id(session, connection_id)
    if connection is None or not connection.enabled:
        raise errors.SamlConnectionNotFound()
    org = await tenancy.org_ref_by_id(session, connection.org_id)
    if org is None:
        raise errors.SamlConnectionNotFound()
    request_id = sso_state.verify_state(settings, state=relay_state, org_slug=org.slug)
    identity = (
        saml.verify_response(
            _our_side(settings, connection.id),
            _idp(connection),
            saml_response=saml_response,
            request_id=request_id,
        )
        if request_id is not None
        else None
    )
    if identity is None:
        return _frontend_callback(settings, org.slug, error=errors.SsoVerificationFailed.code)
    handoff = sso_state.issue_assertion(
        settings,
        org_slug=org.slug,
        email=identity.email,
        name=identity.name,
        subject=identity.subject,
        now=now,
    )
    return _frontend_callback(settings, org.slug, token=handoff)


def identity_from_handoff(settings: Settings, *, token: str, org_slug: str) -> SsoIdentity | None:
    """Who the assertion consumer verified, from the hand-off the frontend posted back."""
    verified = sso_state.verify_assertion(settings, token=token, org_slug=org_slug)
    if verified is None:
        return None
    email, name, subject = verified
    return SsoIdentity(email=email, name=name, subject=subject)


async def read_connection(
    session: AsyncSession, org_slug: str, *, settings: Settings
) -> schemas.SamlConnectionRead:
    """This organisation's SAML connection, for the platform console."""
    org = await tenancy.org_ref_by_slug(session, org_slug)
    if org is None:
        raise errors.SsoNotConfigured()
    connection = await repository.saml_connection_for_org(session, org.id)
    if connection is None:
        raise errors.SamlConnectionNotFound()
    return _read(connection, org_slug, settings)


async def save_connection(
    session: AsyncSession, org_slug: str, body: schemas.SaveSamlConnection, *, settings: Settings
) -> schemas.SamlConnectionRead:
    """Write an organisation's SAML connection. Platform admin only, as the rest of SSO is."""
    org = await tenancy.org_ref_by_slug(session, org_slug)
    if org is None:
        raise errors.SsoNotConfigured()
    if not saml.is_certificate(body.idp_x509_cert):
        raise errors.InvalidSamlConnection("idp_x509_cert is not a certificate")
    connection = await repository.save_saml_connection(
        session,
        org.id,
        idp_entity_id=body.idp_entity_id.strip(),
        idp_sso_url=body.idp_sso_url.strip(),
        idp_x509_cert=body.idp_x509_cert.strip(),
        email_attribute=body.email_attribute.strip(),
        first_name_attribute=body.first_name_attribute,
        last_name_attribute=body.last_name_attribute,
        display_name_attribute=body.display_name_attribute,
        enabled=body.enabled,
    )
    return _read(connection, org_slug, settings)


async def _enabled_connection(session: AsyncSession, org_id: uuid.UUID) -> OrganizationSamlConnection:
    """The organisation's switched-on connection, or the discovery 404."""
    connection = await repository.saml_connection_for_org(session, org_id)
    if connection is None or not connection.enabled:
        raise errors.SsoNotConfigured()
    return connection


def _frontend_callback(settings: Settings, org_slug: str, **params: str) -> str:
    """The frontend page every provider's sign-in comes back to."""
    query = urlencode({"org_slug": org_slug, **params})
    return f"{settings.frontend_url.rstrip('/')}/auth/sso/callback?{query}"


def _read(
    connection: OrganizationSamlConnection, org_slug: str, settings: Settings
) -> schemas.SamlConnectionRead:
    """A stored connection, with the SP URLs its IdP needs."""
    ours = _our_side(settings, connection.id)
    return schemas.SamlConnectionRead(
        id=connection.id,
        org_slug=org_slug,
        idp_entity_id=connection.idp_entity_id,
        idp_sso_url=connection.idp_sso_url,
        idp_x509_cert=connection.idp_x509_cert,
        email_attribute=connection.email_attribute,
        first_name_attribute=connection.first_name_attribute,
        last_name_attribute=connection.last_name_attribute,
        display_name_attribute=connection.display_name_attribute,
        enabled=connection.enabled,
        sp_entity_id=ours.entity_id,
        sp_acs_url=ours.acs_url,
        sp_metadata_url=ours.entity_id,
    )
