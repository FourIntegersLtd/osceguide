"""Credential and session rules.

Pure: no database, no hashing library, no HTTP. The argon2 call lives in the
service, because which hasher we use is an implementation choice; *what counts
as an acceptable password* and *when a refresh token is still good* are rules,
and rules are tested here without a container.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

MIN_PASSWORD_LENGTH = 12

# Routes a user may still reach while holding a temporary password. Reading
# yourself is allowed so the client can show who is signed in and why it is
# being asked to change the password, and capabilities so the shell can render.
#
# Named by OpenAPI operation id (`<tag>_<function>`), which is what `core.auth` matches a
# request against.
ROUTES_ALLOWED_WHILE_PASSWORD_EXPIRED = frozenset(
    {
        "identity_change_password",
        "identity_logout",
        "identity_read_me",
        "tenancy_read_capabilities",
    }
)


class WeakPassword(Exception):
    """Raised by the domain; the service turns it into a `weak_password` AppError."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


# The two arms whose existing tokens this platform will accept in trade for one of its own,
# until the backends behind them are decommissioned. A closed set, because the name selects
# the signing secret the token is verified against — an open one would let a caller choose
# the key it is checked with.
LEGACY_PROVIDERS: Final[tuple[str, ...]] = ("consumer", "institution")


class LegacyTokenUnusable(Exception):
    """Raised by the rule; the service turns it into `invalid_legacy_token`."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def legacy_email(claims: Mapping[str, Any]) -> str:
    """The address a verified legacy token speaks for.

    The address is the join, not `sub`: one subject is a Firestore document id and the
    other a Supabase row id. The migration merges them on lowercased email, so this must
    normalise the same way or an exchange would miss the row the import created.
    """
    raw = claims.get("email")
    if not isinstance(raw, str) or not raw.strip():
        raise LegacyTokenUnusable("the token carries no email address")
    return normalize_email(raw)


def normalize_email(raw: str) -> str:
    """One person is one row. The migration merged legacy user tables on this value, so it
    must stay the same function everywhere."""
    return raw.strip().lower()


def password_for_hashing(raw: str) -> str:
    """The password exactly as typed.

    Deliberately not stripped: trimming silently stores something other than
    what the user chose, and they cannot sign in with what they typed.
    """
    return raw


def validate_password(raw: str) -> None:
    """Refuse a password that is too short, or that mixes fewer than two of
    lower case, upper case, digit and punctuation — raises `WeakPassword`
    rather than returning a verdict, since every caller's next step on
    failure is the same: stop and tell the person why."""
    if len(raw) < MIN_PASSWORD_LENGTH:
        raise WeakPassword(f"Use at least {MIN_PASSWORD_LENGTH} characters")
    classes = (
        any(character.islower() for character in raw),
        any(character.isupper() for character in raw),
        any(character.isdigit() for character in raw),
        any(not character.isalnum() for character in raw),
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
    """Whether a presented refresh token may be exchanged, and why not.

    `revoke_chain` is set only for reuse: the chain must die even though this
    one request is refused, because a spent token being presented again means
    somebody else already holds it.
    """

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
    """Whether this route may run for an account holding a temporary password.

    Everything is refused except the handful of routes named in
    `ROUTES_ALLOWED_WHILE_PASSWORD_EXPIRED`, so a forced reset cannot be
    sidestepped by simply calling some other route instead.
    """
    if not must_change_password:
        return True
    return route in ROUTES_ALLOWED_WHILE_PASSWORD_EXPIRED
