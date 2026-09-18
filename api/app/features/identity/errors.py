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


class UserNotFound(NotFound):
    """No such account.

    Answered only to a platform administrator: everywhere else, a person who
    is not yours is `forbidden` rather than `not found`, so membership cannot
    be probed by response code.

    Mirrors `tenancy.errors.UserNotFound` rather than importing it, for the
    same reason `UnknownExamError` is mirrored: a slice owns its exception
    types and `tenancy` sits above this one. The *code* is deliberately shared
    — it is the API contract — and a unit test pins the two together.
    """

    code = "user_not_found"
    default_message = "No such user"


class InvalidLegacyToken(Unauthenticated):
    """A legacy token that does not verify, has expired, or names no address.

    One code for every one of those, for the reason `InvalidCredentials` has
    one: the client's next move is identical — send the person back to the
    legacy login — and distinguishing them tells an attacker which half of a
    forged token to fix.
    """

    code = "invalid_legacy_token"  # noqa: S105 — an error code, not a secret
    default_message = "Sign in again"


class LegacyAccountNotImported(Unauthenticated):
    """The token verified, but no platform account holds that address.

    Deliberately its own code rather than `invalid_legacy_token`. The caller
    proved they hold that address by presenting a signed token for it, so
    naming the condition reveals nothing they did not already know, and the
    frontend needs to tell those two apart: this one means "stay on the legacy
    backend", not "sign in again".
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
