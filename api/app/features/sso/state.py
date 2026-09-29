"""SEC-015: a stateless, signed `state` for the OIDC code flow.

The platform keeps no session between sending a browser to the identity
provider and the provider sending it back (ADR 0004), so the anti-forgery
`state` and the OIDC `nonce` cannot live in a cookie. Instead they travel in a
short-lived JWT the platform signs with its own `jwt_secret`: the provider
echoes it back on the redirect, and the callback verifies the signature before
trusting the nonce inside. A `state` that was not minted here, was tampered
with, has expired, or was issued for a different organisation verifies as
nothing — so a captured or cross-org `state` cannot be replayed.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime

import jwt

from app.core.logging import get_logger
from app.core.settings import Settings

log = get_logger(__name__)

# Distinct from the access-token type so a state can never be presented as a
# session token, nor a session token as a state.
_PURPOSE = "sso-state"
_TTL_SECONDS = 600  # ten minutes to finish signing in at the provider
_ALGORITHM = "HS256"


def issue_state(
    settings: Settings, *, org_slug: str, now: datetime, nonce: str | None = None
) -> tuple[str, str]:
    """A signed `state` and the `nonce` bound inside it.

    The caller puts both on the provider's sign-in request; the callback
    verifies the state and checks the id token echoes the same nonce, so a
    replayed or injected token is refused. SAML passes its AuthnRequest id as
    the nonce, which the response must name as `InResponseTo`.
    """
    nonce = nonce or secrets.token_urlsafe(24)
    issued_at = int(now.timestamp())
    claims = {
        "iss": settings.jwt_issuer,
        "purpose": _PURPOSE,
        "org_slug": org_slug,
        "nonce": nonce,
        "iat": issued_at,
        "exp": issued_at + _TTL_SECONDS,
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm=_ALGORITHM)
    return token, nonce


def verify_state(settings: Settings, *, state: str, org_slug: str) -> str | None:
    """The nonce a valid `state` carries, or None.

    Valid means: signed by this platform, not expired, minted for the SSO flow,
    and for the same organisation the callback claims to be for — so a state
    issued for one org cannot be replayed against another.
    """
    try:
        claims = jwt.decode(
            state,
            settings.jwt_secret,
            algorithms=[_ALGORITHM],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iss"]},
        )
    except jwt.InvalidTokenError as exc:
        log.warning("sso state failed verification", error=str(exc))
        return None
    if claims.get("purpose") != _PURPOSE:
        return None
    if claims.get("org_slug") != org_slug:
        return None
    nonce = claims.get("nonce")
    return str(nonce) if nonce else None


# --- the SAML hand-off (E-20) ----------------------------------------------------
#
# A SAML response is posted by the browser to this API, not to the frontend, and
# the platform sets no cookies (ADR 0004). So once the assertion consumer has
# verified the response, it hands the browser to the frontend callback page with
# this short-lived signed statement of who was verified; the page posts it to
# `POST /auth/sso/callback` like any other provider's token, and that is where the
# person is provisioned and the session minted.

_ASSERTION_PURPOSE = "saml-assertion"
_ASSERTION_TTL_SECONDS = 120


def issue_assertion(
    settings: Settings, *, org_slug: str, email: str, name: str, subject: str, now: datetime
) -> str:
    """A signed, two-minute statement that the IdP vouched for this person."""
    issued_at = int(now.timestamp())
    claims = {
        "iss": settings.jwt_issuer,
        "purpose": _ASSERTION_PURPOSE,
        "org_slug": org_slug,
        "email": email,
        "name": name,
        "sub": subject,
        "iat": issued_at,
        "exp": issued_at + _ASSERTION_TTL_SECONDS,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=_ALGORITHM)


def verify_assertion(settings: Settings, *, token: str, org_slug: str) -> tuple[str, str, str] | None:
    """(email, name, subject) from a hand-off this platform minted for this organisation, or None."""
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[_ALGORITHM],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iss", "sub"]},
        )
    except jwt.InvalidTokenError as exc:
        log.warning("saml hand-off failed verification", error=str(exc))
        return None
    if claims.get("purpose") != _ASSERTION_PURPOSE or claims.get("org_slug") != org_slug:
        return None
    email = str(claims.get("email") or "")
    if not email:
        return None
    return email, str(claims.get("name") or ""), str(claims["sub"])
