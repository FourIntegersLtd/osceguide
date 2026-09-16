"""Error vocabulary for identity. The class carries the status and the code."""

from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, Unauthenticated


class EmailTaken(Conflict):
    code = "email_taken"
    default_message = "That email address is already registered"


class WeakPasswordError(InvalidInput):
    code = "weak_password"
    default_message = "Choose a stronger password"


class InvalidCredentials(Unauthenticated):
    code = "invalid_credentials"
    # Deliberately the same message whether the address is unknown or the
    # password is wrong: two messages make login an account-enumeration oracle.
    default_message = "Email or password is incorrect"


class InvalidRefreshToken(Unauthenticated):
    code = "invalid_refresh_token"
    default_message = "Sign in again"


class RefreshTokenReused(InvalidRefreshToken):
    """A spent token was presented again, so the chain has leaked.

    Same code as any other refresh failure — the client behaves identically and
    an attacker learns nothing — but the revocation it triggers must survive the
    401, so the effects are committed.
    """

    persist_effects = True


class InvalidResetToken(InvalidInput):
    code = "invalid_reset_token"
    default_message = "That reset link has expired or has already been used"


class AccountSuspended(Unauthenticated):
    code = "account_suspended"
    default_message = "This account is not active"
