"""The legacy login bridge: a session here, in trade for one already held.

No password came across in the migration — the consumer backend hashed with
bcrypt and the institution one with unsalted SHA-256, and neither is worth
rehoming — so an imported person has no credential on this platform at all.
Without this module the only way onto the new backend is a password reset for
every live user, on the weekend of the cutover.

The whole file is deleted at decommission, which is why it is one file: the
verification, the rule and the use case sit together rather than threaded
through `service_sessions.py`, and removing the bridge is removing a module
and one route.

Both retiring backends sign HS256 and set neither `iss` nor `aud`:

- **consumer** (`b2c/shared/services/b2c_token_service.py`) goes through
  flask-jwt-extended, so the payload carries `sub` (a Firestore document id),
  `type: "access"`, `jti`, `iat`, `nbf`, `exp`, `csrf`, and the additional
  claims `email`, `role`, `has_paid`, `app_type`, `plan_end_date`.
- **institution** (`app/features/auth/session.py`) encodes `sub` (a Supabase
  row id), `jti`, `exp` and its claims, `email` among them.

Both expire after thirty days.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Final

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.memberships import MembershipLookup
from app.core.settings import Settings
from app.features.identity import repository
from app.features.identity.domain import LegacyTokenUnusable, legacy_email
from app.features.identity.errors import (
    AccountSuspended,
    InvalidLegacyToken,
    LegacyAccountNotImported,
    LegacyExchangeUnavailable,
)
from app.features.identity.schemas import SignInResult

_ALGORITHM: Final = "HS256"

# The consumer backend signs its refresh tokens with the same secret as its
# access tokens and they differ only by this claim, so without the check a
# refresh token would buy a platform session. The institution backend sets no
# `type` at all and issues no refresh token, so requiring one there would
# refuse every real token.
_REQUIRED_TYPE: Final[dict[str, str | None]] = {"consumer": "access", "institution": None}


def verifying_secret(provider: str, *, settings: Settings) -> str:
    """The secret that must have signed this token.

    Fails closed, like `require_worker_secret`: an arm with nothing configured
    refuses every exchange rather than skipping verification. An unknown
    provider cannot reach here — the request schema closes the set — but it is
    answered the same way rather than raising `KeyError` past the handler.
    """
    secret = {
        "consumer": settings.legacy_consumer_jwt_secret,
        "institution": settings.legacy_institution_jwt_secret,
    }.get(provider, "")
    if not secret.strip():
        raise LegacyExchangeUnavailable()
    return secret


def decode(token: str, *, provider: str, settings: Settings) -> dict[str, Any]:
    """The claims of a token this platform did not sign.

    `exp` is required and verified: honouring the original expiry is what
    stops the bridge outliving the session it was traded from. No audience is
    checked because neither backend sets one, and asserting a claim that is
    never present would refuse every real token.
    """
    secret = verifying_secret(provider, settings=settings)
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[_ALGORITHM],
            options={"require": ["exp", "sub"], "verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise InvalidLegacyToken() from exc
    expected_type = _REQUIRED_TYPE.get(provider)
    if expected_type is not None and claims.get("type") != expected_type:
        raise InvalidLegacyToken()
    return dict(claims)


async def exchange(
    session: AsyncSession,
    *,
    provider: str,
    token: str,
    memberships_for: MembershipLookup,
    settings: Settings,
    now: datetime,
) -> SignInResult:
    """Verify a token the old backend issued, and answer with a platform pair.

    This is not a password, but it mints a session the same way login does, so
    it goes through the MFA gate. A platform admin cannot skip the second
    factor by trading an old token. SSO does not use this function.

    What it does *not* do is create anybody. An address with no row is
    `legacy_account_not_imported`, so a gap in the import surfaces as a named
    refusal rather than as a second account with none of the person's history.

    It grants no more than `login` does, either. Whatever the presented token
    claims about roles, paid status or org membership is ignored: memberships
    are read from this database, so a stale claim in a thirty-day-old token
    cannot widen anyone's access here.
    """
    claims = decode(token, provider=provider, settings=settings)
    try:
        email = legacy_email(claims)
    except LegacyTokenUnusable as exc:
        raise InvalidLegacyToken() from exc

    user = await repository.user_by_email(session, email)
    if user is None:
        raise LegacyAccountNotImported()
    if user.status != "active":
        raise AccountSuspended()

    memberships = await memberships_for(session, user.id)
    from app.features.identity.service_mfa import finish_password_sign_in

    return await finish_password_sign_in(session, user, settings=settings, now=now, memberships=memberships)
