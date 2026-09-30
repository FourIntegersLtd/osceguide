"""Minting and hashing the secrets identity hands out.

Nothing here touches the database; it is the cryptographic plumbing the service composes.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from app.core.auth import Principal, issue_access_token
from app.core.settings import Settings
from app.features.identity.domain import password_for_hashing

# Distinct from the access token's `typ`, so `decode_access_token` refuses
# these as a bearer. A challenge is not a session.
MFA_CHALLENGE_TYPE = "mfa_challenge"  # noqa: S105 — a token type, not a secret
MFA_ENROL_TYPE = "mfa_enrol"  # noqa: S105 — a token type, not a secret

_hasher = PasswordHasher()

# The client holds a random string; only its SHA-256 reaches the database, so
# a database leak does not hand over live sessions. SHA-256 rather than argon2
# because the input already has full entropy — there is nothing to slow down.
TOKEN_BYTES = 32


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_token() -> tuple[str, str]:
    """A fresh random secret, and the hash of it that alone reaches storage."""
    raw = secrets.token_urlsafe(TOKEN_BYTES)
    return raw, hash_token(raw)


def hash_password(raw: str) -> str:
    return _hasher.hash(password_for_hashing(raw))


def verify_password(password_hash: str | None, raw: str) -> bool:
    """Whether this password matches the stored hash. Refuses (returns
    False) rather than raises for a missing hash, a wrong password, or a
    hash argon2 itself calls unreadable — every one of those is simply not
    a match, not a reason to stop the caller."""
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password_for_hashing(raw))
    except (VerifyMismatchError, VerificationError):
        return False


def access_token_for(principal: Principal, *, settings: Settings, now: datetime) -> str:
    return issue_access_token(principal, settings=settings, now=now)


def issue_mfa_challenge(
    user_id: UUID, *, token_type: str, ttl_seconds: int, settings: Settings, now: datetime
) -> str:
    """A short-lived JWT that names who just passed the password, and nothing else.

    `token_type` is `mfa_challenge` once an authenticator is confirmed, or
    `mfa_enrol` when policy requires one that does not exist yet. It carries
    no memberships and is not an access token.
    """
    claims = {
        "iss": settings.jwt_issuer,
        "sub": str(user_id),
        "typ": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")


def read_mfa_challenge(token: str, *, expected_type: str, settings: Settings) -> UUID:
    """The user id a challenge names, or raise `jwt.PyJWTError`.

    The caller turns that into `mfa_challenge_expired`. A token of the wrong
    `typ` is the same refusal: an enrolment challenge cannot verify, and a
    verify challenge cannot enrol.
    """
    claims = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        issuer=settings.jwt_issuer,
        options={"require": ["exp", "iat", "sub"]},
    )
    if claims.get("typ") != expected_type:
        raise jwt.InvalidTokenError("wrong challenge type")
    return UUID(claims["sub"])


# A hash to verify against when the address is unknown, so a miss costs the
# same argon2 work as a hit. Without it, login answers in microseconds for an
# address that does not exist and tens of milliseconds for one that does,
# which is an account-enumeration oracle wearing an identical error message.
_ABSENT_USER_HASH = _hasher.hash("password-for-an-account-that-does-not-exist")


def verify_absent_password(raw: str) -> bool:
    """Spend the same argon2 time an unknown address's login would, then
    always refuse. Called so that address-not-found and wrong-password take
    the same wall-clock time, which is what stops timing from being a
    second, unofficial account-enumeration oracle alongside the message."""
    verify_password(_ABSENT_USER_HASH, raw)
    return False
