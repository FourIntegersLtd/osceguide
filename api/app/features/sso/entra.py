"""The Entra adapter behind `core.ports.SsoBroker`: direct OIDC, no broker
in between.

One multi-tenant app registration (`ENTRA_CLIENT_ID`/`ENTRA_CLIENT_SECRET`)
serves every institution; `organization_sso.issuer` carries each
institution's own Entra tenant id, which is what tells a multi-tenant
registration which directory to authenticate against. Unlike Clerk, the
token this broker is handed back is not itself proof of anything — it is an
authorization code from the standard OIDC code flow, exchanged here for an
id token that is then verified against Entra's own signing keys before
anybody is trusted.

No refresh token is kept: the platform issues its own session (ADR 0004),
and Entra's token is spent the moment it has answered who signed in.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlencode

import httpx
import jwt
from jwt import PyJWKClient

from app.core.logging import get_logger
from app.core.ports import SsoBrokerUnavailable, SsoIdentity
from app.core.settings import Settings

log = get_logger(__name__)

AUTHORIZE_PATH = "/oauth2/v2.0/authorize"
TOKEN_PATH = "/oauth2/v2.0/token"  # noqa: S105 - a URL path, not a credential
JWKS_PATH = "/discovery/v2.0/keys"
SCOPE = "openid email profile"
TIMEOUT_SECONDS = 15.0


def _authority(tenant_id: str) -> str:
    return f"https://login.microsoftonline.com/{tenant_id}"


class EntraBroker:
    """Runs the authorization-code flow against one institution's Entra tenant.

    Stateless between the two calls: `sign_in_url` and `verify` are both
    handed the tenant id fresh (`organization_sso.issuer`), because nothing
    here is per-request state — the client id and secret are the whole app
    registration and are the same for every institution.
    """

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    def sign_in_url(self, *, redirect_url: str, issuer: str | None) -> str:
        """Entra's own consent/sign-in page for this institution's tenant.

        `issuer` here is the tenant id (a GUID), not a full issuer URL — the
        same field Clerk stores its frontend domain in, read as whichever
        shape the configured provider expects.
        """
        tenant_id = (issuer or "").strip()
        if not tenant_id:
            raise SsoBrokerUnavailable("This organisation has no Entra tenant id configured")
        params = {
            "client_id": self._client_id,
            "response_type": "code",
            "redirect_uri": redirect_url,
            "response_mode": "query",
            "scope": SCOPE,
        }
        return f"{_authority(tenant_id)}{AUTHORIZE_PATH}?{urlencode(params, quote_via=quote)}"

    async def verify(self, *, token: str, issuer: str | None = None) -> SsoIdentity | None:
        """Exchange an authorization code for an id token, then verify it.

        `token` is the `code` Entra's redirect appended, not a bearer token —
        the one real difference from Clerk's flow, which already had a
        session to check. Two things must hold before anybody is trusted:
        the id token's signature checks out against Entra's own published
        keys for this tenant, and its `aud`/`iss` name this app registration
        and this tenant — otherwise a token minted for a different
        application, or a different institution's tenant, would verify here
        too.
        """
        tenant_id = (issuer or "").strip()
        if not tenant_id:
            raise SsoBrokerUnavailable("This organisation has no Entra tenant id configured")
        authority = _authority(tenant_id)
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                exchanged = await client.post(
                    f"{authority}{TOKEN_PATH}",
                    data={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "grant_type": "authorization_code",
                        "code": token,
                        "scope": SCOPE,
                    },
                )
                if exchanged.status_code >= 400:
                    log.warning("entra refused a code exchange", status=exchanged.status_code)
                    return None
                id_token = str(exchanged.json().get("id_token") or "")
                if not id_token:
                    return None
                jwks_client = PyJWKClient(f"{authority}{JWKS_PATH}", timeout=TIMEOUT_SECONDS)
                signing_key = jwks_client.get_signing_key_from_jwt(id_token)
        except httpx.HTTPError as exc:
            raise SsoBrokerUnavailable(f"could not reach Entra: {exc}") from exc
        except jwt.PyJWKClientError as exc:
            log.warning("entra id token names no key this tenant publishes", error=str(exc))
            return None

        try:
            claims: dict[str, Any] = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._client_id,
                issuer=f"{authority}/v2.0",
            )
        except jwt.InvalidTokenError as exc:
            log.warning("entra id token failed verification", error=str(exc))
            return None

        email = str(claims.get("email") or claims.get("preferred_username") or "")
        subject = str(claims.get("oid") or claims.get("sub") or "")
        if not email or not subject:
            return None
        return SsoIdentity(email=email, name=str(claims.get("name") or ""), subject=subject)


def build_entra_broker(settings: Settings) -> EntraBroker:
    """The adapter, or a refusal. Never a silent no-op — same shape as Clerk's."""
    if not settings.entra_client_id.strip() or not settings.entra_client_secret.strip():
        raise SsoBrokerUnavailable(
            "ENTRA_CLIENT_ID/ENTRA_CLIENT_SECRET are not set, so this deployment cannot offer Entra SSO"
        )
    return EntraBroker(settings.entra_client_id, settings.entra_client_secret)
