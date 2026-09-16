"""Minting and hashing the secrets identity hands out.

Separated from `service.py` so the use cases read as use cases. Nothing here
touches the database; it is the cryptographic plumbing the service composes.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from app.core.auth import Membership, Principal, issue_access_token
from app.core.settings import Settings
from app.features.identity.domain import password_for_hashing
from app.features.identity.schemas import TokenPair

_hasher = PasswordHasher()

# The client holds a random string; only its SHA-256 reaches the database, so
# a database leak does not hand over live sessions. SHA-256 rather than argon2
# because the input already has full entropy — there is nothing to slow down.
TOKEN_BYTES = 32


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(TOKEN_BYTES)
    return raw, hash_token(raw)


def hash_password(raw: str) -> str:
    return _hasher.hash(password_for_hashing(raw))


def verify_password(password_hash: str | None, raw: str) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password_for_hashing(raw))
    except (VerifyMismatchError, VerificationError):
        return False


def principal_for(
    *, user_id: object, email: str, is_platform_admin: bool, memberships: list[Membership]
) -> Principal:
    return Principal(
        user_id=user_id,  # type: ignore[arg-type]
        email=email,
        memberships=tuple(memberships),
        active_org_slug=memberships[0].org_slug if memberships else None,
        is_platform_admin=is_platform_admin,
    )


def access_token_for(principal: Principal, *, settings: Settings, now: datetime) -> str:
    return issue_access_token(principal, settings=settings, now=now)


def refresh_expiry(settings: Settings, now: datetime) -> datetime:
    return now + timedelta(seconds=settings.jwt_refresh_ttl_seconds)


def token_pair(access: str, refresh: str, settings: Settings) -> TokenPair:
    return TokenPair(access_token=access, refresh_token=refresh, expires_in=settings.jwt_access_ttl_seconds)
