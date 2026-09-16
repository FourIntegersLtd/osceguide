"""Credential and session rules.

Pure: no database, no hashing library, no HTTP. The argon2 call lives in the
service, because which hasher we use is an implementation choice; *what counts
as an acceptable password* and *when a refresh token is still good* are rules,
and rules are tested here without a container.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

MIN_PASSWORD_LENGTH = 12

# Routes a user may still reach while holding a temporary password. Reading
# yourself is allowed so the client can show who is signed in and why it is
# being asked to change the password.
ROUTES_ALLOWED_WHILE_PASSWORD_EXPIRED = frozenset({"auth.change_password", "auth.logout", "me.read"})


class WeakPassword(Exception):
    """Raised by the domain; the service turns it into a `weak_password` AppError."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def normalize_email(raw: str) -> str:
    """One person is one row.

    The migration merges b2c's four per-product user collections and b2b_users
    on this value, so it has to be the same function everywhere, forever.
    """
    return raw.strip().lower()


def password_for_hashing(raw: str) -> str:
    """The password exactly as typed.

    Deliberately not stripped: trimming silently stores something other than
    what the user chose, and they cannot sign in with what they typed.
    """
    return raw


def validate_password(raw: str) -> None:
    if len(raw) < MIN_PASSWORD_LENGTH:
        raise WeakPassword(f"Use at least {MIN_PASSWORD_LENGTH} characters")
    classes = (
        any(c.islower() for c in raw),
        any(c.isupper() for c in raw),
        any(c.isdigit() for c in raw),
        any(not c.isalnum() for c in raw),
    )
    if sum(classes) < 2:
        raise WeakPassword("Mix letters with numbers, punctuation, or capitals")


@dataclass(frozen=True)
class RefreshChain:
    """One sign-in. Rotating a token replaces `current_token_id` in place."""

    chain_id: str
    current_token_id: str
    expires_at: datetime
    revoked_at: datetime | None = None


@dataclass(frozen=True)
class RefreshDecision:
    accepted: bool
    revoke_chain: bool = False
    reason: str | None = None


def use_refresh_token(chain: RefreshChain, *, presented_token_id: str, now: datetime) -> RefreshDecision:
    """Whether a presented refresh token may be exchanged.

    Presenting a token that has already been rotated means two parties hold
    tokens from one chain, so the chain has leaked. Refusing just this request
    would leave the thief's freshly rotated token working, so the whole chain
    dies and the real user signs in again.
    """
    if chain.revoked_at is not None:
        return RefreshDecision(accepted=False, reason="revoked")
    if now >= chain.expires_at:
        return RefreshDecision(accepted=False, reason="expired")
    if presented_token_id != chain.current_token_id:
        return RefreshDecision(accepted=False, revoke_chain=True, reason="reuse_detected")
    return RefreshDecision(accepted=True)


def may_call(*, must_change_password: bool, route: str) -> bool:
    if not must_change_password:
        return True
    return route in ROUTES_ALLOWED_WHILE_PASSWORD_EXPIRED
