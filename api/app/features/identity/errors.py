"""Error vocabulary for identity. The class carries the status and the code."""

from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, NotFound, Unauthenticated, Unavailable


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


class PasswordLoginDisabled(Unauthenticated):
    """Distinct from `InvalidCredentials` on purpose: the account's organisation already
    publishes that it signs in through SSO (`GET /auth/sso/sign-in`), so naming this leaks
    nothing a visitor could not already learn."""

    code = "password_login_disabled"
    default_message = (
        "This account signs in through your organisation. Use your organisation's sign-in instead."
    )


class UserNotFound(NotFound):
    """No such account.

    Answered only to a platform administrator: everywhere else, a person who is not yours is
    `forbidden` rather than `not found`, so membership cannot be probed by response code.

    Mirrors `tenancy.errors.UserNotFound` rather than importing it — each slice owns its
    exception types. The *code* is the shared API contract, pinned together by a unit test.
    """

    code = "user_not_found"
    default_message = "No such user"


class InvalidLegacyToken(Unauthenticated):
    """A legacy token that does not verify, has expired, or names no address.

    One code for all of those: the client's next move is identical, and distinguishing them
    would tell an attacker which half of a forged token to fix.
    """

    code = "invalid_legacy_token"  # noqa: S105 — an error code, not a secret
    default_message = "Sign in again"


class LegacyAccountNotImported(Unauthenticated):
    """The token verified, but no platform account holds that address.

    Its own code rather than `invalid_legacy_token`: the frontend needs to tell them apart —
    this one means "stay on the legacy backend", not "sign in again".
    """

    code = "legacy_account_not_imported"
    default_message = "This account has not been migrated yet"


class LegacyExchangeUnavailable(Unavailable):
    """No verifying secret is configured for that legacy backend.

    Fails closed, like the worker guard: an unset secret must refuse every
    exchange rather than accept an unverified token.
    """

    code = "legacy_exchange_unavailable"
    default_message = "Legacy sign-in is not available here"
