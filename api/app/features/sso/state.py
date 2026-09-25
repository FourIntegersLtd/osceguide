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


def issue_state(settings: Settings, *, org_slug: str, now: datetime) -> tuple[str, str]:
    """A signed `state` and the `nonce` bound inside it.

    The caller puts both on the provider's sign-in request; the callback
    verifies the state and checks the id token echoes the same nonce, so a
    replayed or injected token is refused.
    """
    nonce = secrets.token_urlsafe(24)
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
