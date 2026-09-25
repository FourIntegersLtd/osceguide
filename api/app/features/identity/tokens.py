"""Minting and hashing the secrets identity hands out.

Nothing here touches the database; it is the cryptographic plumbing the service composes.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from app.core.auth import Principal, issue_access_token
from app.core.settings import Settings
from app.features.identity.domain import password_for_hashing

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


def access_token_for(principal: Principal, *, settings: Settings, now: datetime) -> str:
    return issue_access_token(principal, settings=settings, now=now)


# A hash to verify against when the address is unknown, so a miss costs the
# same argon2 work as a hit. Without it, login answers in microseconds for an
# address that does not exist and tens of milliseconds for one that does,
# which is an account-enumeration oracle wearing an identical error message.
_ABSENT_USER_HASH = _hasher.hash("password-for-an-account-that-does-not-exist")


def verify_absent_password(raw: str) -> bool:
    verify_password(_ABSENT_USER_HASH, raw)
    return False
