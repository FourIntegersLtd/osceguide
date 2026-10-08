"""Error vocabulary for identity. The class carries the status and the code."""

from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, NotFound, Unauthenticated, Unavailable


class EmailTaken(Conflict):
    """Refuses registration for an address another account already holds."""

    code = "email_taken"
    default_message = "That email address is already registered"


class WeakPasswordError(InvalidInput):
    """Refuses a password `domain.validate_password` rejects."""

    code = "weak_password"
    default_message = "Choose a stronger password"


class InvalidCredentials(Unauthenticated):
    """Refuses a sign-in whose address is unknown or whose password is wrong."""

    code = "invalid_credentials"
    # Deliberately the same message whether the address is unknown or the
    # password is wrong: two messages make login an account-enumeration oracle.
    default_message = "Email or password is incorrect"


class AccountNotFound(Unauthenticated):
    """A valid token names an account that has been deleted or erased.

    Not `InvalidCredentials`: the web client reads that code as a wrong password typed on a
    screen and keeps the session, whereas this one means the session is dead.
    """

    code = "account_not_found"
    default_message = "Sign in again"


class InvalidRefreshToken(Unauthenticated):
    """Refuses a refresh token that is unknown, expired, or already revoked."""

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
    """Refuses a password-reset token that is unknown, expired, or spent."""

    code = "invalid_reset_token"
    default_message = "That reset link has expired or has already been used"


class AccountSuspended(Unauthenticated):
    """Refuses sign-in for an account whose status is not `active`."""

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


class PasswordNotSet(Conflict):
    """A signed-in account with no password to prove (an invitation
    accepted through SSO, or a magic link): it sets one through a reset link."""

    code = "password_not_set"
    default_message = "This account has no password yet. Ask for a reset link to set one."


class ExamAlreadyChosen(Conflict):
    """The account already has an exam, and it cannot be changed from the account itself.

    The exam decides which library, material and peers a person sees, and moving somebody is a
    support action against what they have bought (the platform console's user profile).
    """

    code = "exam_already_chosen"
    default_message = "Your exam is already set. Contact support to switch exams."


class UnknownExamError(NotFound):
    """Mirrors `catalog.errors.UnknownExamError`, and shares its code: no published exam has
    this code, so choosing it would open an account on nothing."""

    code = "unknown_exam"
    default_message = "No such exam"


class InvalidAvatarFile(InvalidInput):
    """The uploaded file is not a small image."""

    code = "invalid_avatar_file"
    default_message = "That file cannot be used as a profile photo"


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


class InvalidMfaCode(Unauthenticated):
    """A TOTP or recovery code that does not match, or a TOTP step already used."""

    code = "invalid_mfa_code"
    default_message = "That code is not valid"


class MfaChallengeExpired(Unauthenticated):
    """The sign-in challenge is missing, signed wrong, the wrong kind, or past its expiry."""

    code = "mfa_challenge_expired"
    default_message = "That sign-in challenge has expired. Sign in again."


class MfaRequiredByPolicy(Conflict):
    """Refuses turning MFA off for an account the policy says must keep it."""

    code = "mfa_required_by_policy"
    default_message = "This account must keep two-factor sign-in"


class MfaAlreadyEnrolled(Conflict):
    """An authenticator is already confirmed, so enrolment cannot start again."""

    code = "mfa_already_enrolled"
    default_message = "An authenticator is already set up"


class MfaNotEnrolled(Conflict):
    """No confirmed authenticator, so there is nothing to verify, disable or reset."""

    code = "mfa_not_enrolled"
    default_message = "This account has no authenticator set up"


class LegacyExchangeUnavailable(Unavailable):
    """No verifying secret is configured for that legacy backend.

    Fails closed, like the worker guard: an unset secret must refuse every
    exchange rather than accept an unverified token.
    """

    code = "legacy_exchange_unavailable"
    default_message = "Legacy sign-in is not available here"
