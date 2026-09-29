"""Starting and finishing an SSO sign-in.

`service.py` reads and writes the arrangement; this module runs the login
itself. The broker is a port (`core.ports.SsoBroker`), so the flow is tested
against a fake and Clerk or Entra are adapters behind it.

The platform owns the session (ADR 0004): the broker only answers who signed
in. Provisioning the person and minting the token are `identity`'s job; the
organisation's name and existence are `tenancy`'s.
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlencode

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.memberships import MembershipLookup
from app.core.ports import SsoBroker, SsoBrokerUnavailable, SsoIdentity
from app.core.settings import Settings, SettingsDep
from app.features.identity import service_sso
from app.features.sso import domain, errors, repository, schemas, service_saml
from app.features.sso import state as sso_state
from app.features.sso.models import OrganizationSso
from app.features.tenancy import service as tenancy


class SsoBrokers:
    """Both adapters, selected by the organisation's own configured provider.

    Neither adapter holds per-tenant state — Entra's tenant id and Clerk's
    frontend domain both travel as `issuer` on each call — so one instance
    of each serves every organisation that names it.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def for_provider(self, provider: domain.Provider) -> SsoBroker:
        """The adapter for this provider, or refuse `sso_login_unavailable`
        if its secret is not configured on this deployment."""
        # Imported here, not at module load: a deployment with neither
        # provider configured must still be able to import this module.
        from app.features.sso.clerk import build_clerk_broker  # noqa: PLC0415
        from app.features.sso.entra import build_entra_broker  # noqa: PLC0415

        builder = build_clerk_broker if provider is domain.Provider.CLERK else build_entra_broker
        try:
            return builder(self._settings)
        except SsoBrokerUnavailable as exc:
            raise errors.SsoLoginUnavailable() from exc


def get_sso_broker(settings: SettingsDep) -> SsoBrokers:
    """The broker selector, as the router's dependency. Overridden in tests.

    `SettingsDep` rather than a bare `Settings` for the reason `billing`'s
    `get_checkout` gives: FastAPI reads a dependency's own signature, and an
    un-annotated pydantic model there is taken for a second request body.
    """
    return SsoBrokers(settings)


async def _enabled_config(session: AsyncSession, org_slug: str) -> OrganizationSso:
    """The arrangement to sign in against, or the same 404 discovery gives.

    A configuration that is switched off is not something to run a login
    against, and the answer is the same as never having had one: sign in here,
    with a password.
    """
    org = await tenancy.org_ref_by_slug(session, org_slug)
    if org is None:
        raise errors.SsoNotConfigured()
    config = await repository.config_for_org(session, org.id)
    if config is None or not config.enabled:
        raise errors.SsoNotConfigured()
    return config


def _configured_provider(config: OrganizationSso) -> domain.Provider:
    """The provider this arrangement names, or `sso_provider_unsupported`
    for a stored value nothing here can read — never `invalid_provider`,
    which is a write-time refusal, not a read-time one."""
    try:
        return domain.normalise_provider(config.provider)
    except domain.InvalidProvider as exc:
        raise errors.SsoProviderUnsupported() from exc


def _callback_redirect_url(settings: Settings, org_slug: str) -> str:
    """Where the broker sends the browser back to.

    A frontend page, not this API: the platform issues no cookies (ADR 0004),
    so the page posts the appended token to `POST /auth/sso/callback`. The
    slug rides along so the callback knows which arrangement to verify
    against without trusting the token to say.
    """
    base = settings.frontend_url.rstrip("/")
    return f"{base}/auth/sso/callback?{urlencode({'org_slug': org_slug})}"


def _requires_state(provider: domain.Provider) -> bool:
    """Whether this provider runs the OIDC code flow the SEC-015 `state` guards.

    Entra does — its redirect echoes `state` and its id token carries the
    `nonce`. Clerk verifies its own session token and carries neither, so a
    missing `state` on a Clerk callback is not a failure.
    """
    return provider is domain.Provider.ENTRA


async def build_login(
    session: AsyncSession, org_slug: str, *, brokers: SsoBrokers, settings: Settings, now: datetime
) -> schemas.SsoLoginResult:
    """Where to send this organisation's people to sign in."""
    config = await _enabled_config(session, org_slug)
    provider = _configured_provider(config)
    if provider is domain.Provider.SAML:
        # SAML is not a broker call: the request is built and bound to the
        # signed state here, and the IdP posts back to our own consumer.
        url = await service_saml.sign_in_url(session, config.org_id, org_slug, settings=settings, now=now)
        return schemas.SsoLoginResult(sign_in_url=url)
    broker = brokers.for_provider(provider)
    # SEC-015: a signed, short-lived state carries a fresh nonce back to the
    # callback (the platform stores nothing between the two — ADR 0004).
    state, nonce = sso_state.issue_state(settings, org_slug=org_slug, now=now)
    try:
        url = broker.sign_in_url(
            redirect_url=_callback_redirect_url(settings, org_slug),
            issuer=config.issuer,
            state=state,
            nonce=nonce,
        )
    except SsoBrokerUnavailable as exc:
        raise errors.SsoLoginUnavailable() from exc
    return schemas.SsoLoginResult(sign_in_url=url)


async def complete_callback(
    session: AsyncSession,
    org_slug: str,
    *,
    token: str,
    state: str | None,
    brokers: SsoBrokers,
    settings: Settings,
    now: datetime,
    memberships_for: MembershipLookup,
) -> schemas.SsoSession:
    """Verify the broker's token, provision the person, answer with a session."""
    config = await _enabled_config(session, org_slug)
    provider = _configured_provider(config)
    if provider is domain.Provider.SAML:
        # The assertion consumer has already verified the IdP's signed response
        # and its `InResponseTo`; what arrives here is its signed hand-off.
        identity = service_saml.identity_from_handoff(settings, token=token, org_slug=org_slug)
    else:
        identity = await _verified_by_broker(
            brokers.for_provider(provider),
            config,
            provider,
            token=token,
            state=state,
            settings=settings,
            org_slug=org_slug,
        )
    if identity is None:
        raise errors.SsoVerificationFailed()

    auth = await service_sso.sign_in_external(
        session,
        provider=provider.value,
        subject=identity.subject,
        email=identity.email,
        name=identity.name,
        tenant_slug=org_slug,
        exam_code=config.default_exam_code,
        settings=settings,
        now=now,
        memberships_for=memberships_for,
        sso_only=config.sso_only,
    )
    return schemas.SsoSession(
        access_token=auth.access_token,
        refresh_token=auth.refresh_token,
        token_type=auth.token_type,
        expires_in=auth.expires_in,
    )


async def _verified_by_broker(
    broker: SsoBroker,
    config: OrganizationSso,
    provider: domain.Provider,
    *,
    token: str,
    state: str | None,
    settings: Settings,
    org_slug: str,
) -> SsoIdentity | None:
    """Who an OIDC broker (Clerk, Entra) vouches for, with the SEC-015 state checked first."""
    # SEC-015: on the OIDC code flow, the callback must carry the signed state
    # this org's sign-in minted, and the nonce inside it must match the id
    # token. A missing, tampered, expired or cross-org state fails here before
    # the broker is asked, so a forged or replayed callback cannot mint a
    # session.
    expected_nonce: str | None = None
    if _requires_state(provider):
        if not state:
            raise errors.SsoVerificationFailed()
        expected_nonce = sso_state.verify_state(settings, state=state, org_slug=org_slug)
        if expected_nonce is None:
            raise errors.SsoVerificationFailed()
    try:
        return await broker.verify(token=token, issuer=config.issuer, expected_nonce=expected_nonce)
    except SsoBrokerUnavailable as exc:
        raise errors.SsoLoginUnavailable() from exc
