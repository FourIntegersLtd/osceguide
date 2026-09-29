"""A second factor on password sign-in.

Every password path that would otherwise call `issue` comes through
`finish_password_sign_in` first. SSO does not: `sign_in_external` calls
`issue` directly, because the identity provider owns the second factor.
A refresh chain already issued keeps working; the requirement is checked
at the next password sign-in, not on refresh.

Password reset and invitation acceptance do not mint a session. They set a
password, and the next login is the gate.
"""

from __future__ import annotations

import hmac
import secrets
import uuid
from datetime import datetime

import jwt
import pyotp
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.core.memberships import MembershipLookup
from app.core.rate_limit import MFA_VERIFY, check
from app.core.secrets_at_rest import decrypt_text, encrypt_text
from app.core.settings import Settings
from app.features.identity import repository
from app.features.identity.domain import (
    MFA_ENROL_TTL_SECONDS,
    MFA_VERIFY_TTL_SECONDS,
    MfaMembership,
    mfa_required_reason,
)
from app.features.identity.errors import (
    AccountSuspended,
    InvalidMfaCode,
    MfaAlreadyEnrolled,
    MfaChallengeExpired,
    MfaNotEnrolled,
    MfaRequiredByPolicy,
    PasswordLoginDisabled,
)
from app.features.identity.models import User, UserMfa
from app.features.identity.schemas import (
    AuthResult,
    MfaEnrolmentConfirmed,
    MfaEnrolmentRequiredResponse,
    MfaEnrolmentStart,
    MfaRecoveryCodesRead,
    MfaRequiredResponse,
    MfaStatusRead,
    SignInResult,
)
from app.features.identity.service_sessions import issue
from app.features.identity.tokens import (
    MFA_CHALLENGE_TYPE,
    MFA_ENROL_TYPE,
    hash_password,
    issue_mfa_challenge,
    read_mfa_challenge,
    verify_password,
)
from app.features.tenancy import service as tenancy

RECOVERY_CODE_COUNT = 10
TOTP_ISSUER = "OSCE Guide"
TOTP_INTERVAL_SECONDS = 30
TOTP_VALID_WINDOW = 1


def _user_from_challenge(token: str, *, expected_type: str, settings: Settings) -> uuid.UUID:
    """The account a challenge names, or `mfa_challenge_expired` for anything else."""
    try:
        return read_mfa_challenge(token, expected_type=expected_type, settings=settings)
    except (jwt.PyJWTError, ValueError) as exc:
        raise MfaChallengeExpired() from exc


async def _limited_challenge_user(
    token: str, *, expected_type: str, settings: Settings, caller: str
) -> uuid.UUID:
    """Read the challenge, then count this attempt against that user and the caller."""
    user_id = _user_from_challenge(token, expected_type=expected_type, settings=settings)
    await check(MFA_VERIFY, f"{user_id}:{caller}")
    return user_id


def accepted_totp_step(secret: str, code: str, *, now: datetime, last_used_step: int | None) -> int:
    """The 30-second step this code matches, within one step either side of now.

    A step at or before `last_used_step` is a replay of a code already accepted,
    including one that is still inside the window.
    """
    totp = pyotp.TOTP(secret, interval=TOTP_INTERVAL_SECONDS)
    current = totp.timecode(now)
    presented = code.strip()
    for step in range(current + TOTP_VALID_WINDOW, current - TOTP_VALID_WINDOW - 1, -1):
        if step < 0:
            continue
        if hmac.compare_digest(totp.generate_otp(step), presented):
            if last_used_step is not None and step <= last_used_step:
                raise InvalidMfaCode()
            return step
    raise InvalidMfaCode()


def _new_recovery_code() -> str:
    """One recovery code, shown once and stored only as an argon2 hash."""
    raw = secrets.token_hex(4)
    return f"{raw[:4]}-{raw[4:]}"


def _otpauth_uri(secret: str, email: str) -> str:
    """The URI an authenticator app turns into a QR code."""
    return str(
        pyotp.TOTP(secret, interval=TOTP_INTERVAL_SECONDS).provisioning_uri(
            name=email, issuer_name=TOTP_ISSUER
        )
    )


async def _active_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    """The account a challenge may still finish.

    Gone or not active is `mfa_challenge_expired`. Password login switched off
    since the challenge was issued — an `sso_only` sign-in writes that — is
    the same `password_login_disabled` login returns.
    """
    user = await repository.user_by_id(session, user_id)
    if user is None or user.status != "active":
        raise MfaChallengeExpired()
    if user.password_login_disabled:
        raise PasswordLoginDisabled()
    return user


async def _audit(
    session: AsyncSession,
    *,
    actor: User,
    action: str,
    now: datetime,
    summary: str,
    actor_user_id: uuid.UUID | None = None,
    actor_email: str | None = None,
) -> None:
    """A platform audit row for an MFA change. The target is the account it happened to."""
    await tenancy.record_audit(
        session,
        org_id=None,
        actor_user_id=actor.id if actor_user_id is None else actor_user_id,
        actor_email=actor.email if actor_email is None else actor_email,
        action=action,
        at=now,
        target_type="user",
        target_id=str(actor.id),
        summary=summary,
    )


async def finish_password_sign_in(
    session: AsyncSession,
    user: User,
    *,
    settings: Settings,
    now: datetime,
    memberships: list[Membership],
    count_as_login: bool = True,
) -> SignInResult:
    """Mint a session, or a short challenge when a second factor is in the way.

    Called by password login, registration and the legacy token exchange.
    Not called by `sign_in_external`: the identity provider already performed
    the second factor, and asking again would lock out every SSO organisation.
    """
    flags = await tenancy.staff_mfa_flags(session, user.id)
    reason = mfa_required_reason(
        is_platform_admin=user.is_platform_admin,
        memberships=[MfaMembership(role=role, org_requires_staff_mfa=required) for role, required in flags],
    )
    row = await repository.mfa_by_user(session, user.id)
    enrolled = row is not None and row.confirmed_at is not None
    if enrolled:
        return MfaRequiredResponse(
            challenge_token=issue_mfa_challenge(
                user.id,
                token_type=MFA_CHALLENGE_TYPE,
                ttl_seconds=MFA_VERIFY_TTL_SECONDS,
                settings=settings,
                now=now,
            ),
            expires_in=MFA_VERIFY_TTL_SECONDS,
        )
    if reason is not None:
        return MfaEnrolmentRequiredResponse(
            challenge_token=issue_mfa_challenge(
                user.id,
                token_type=MFA_ENROL_TYPE,
                ttl_seconds=MFA_ENROL_TTL_SECONDS,
                settings=settings,
                now=now,
            ),
            expires_in=MFA_ENROL_TTL_SECONDS,
        )
    return await _issue_session(
        session, user, settings=settings, now=now, memberships=memberships, count_as_login=count_as_login
    )


async def _issue_session(
    session: AsyncSession,
    user: User,
    *,
    settings: Settings,
    now: datetime,
    memberships: list[Membership],
    count_as_login: bool,
) -> AuthResult:
    """The session a password sign-in ends in once no second factor is outstanding."""
    if count_as_login:
        await repository.record_login(session, user.id, now)
        user.last_login_at = now
    tokens = await issue(session, user, settings=settings, now=now, memberships=memberships)
    from app.features.identity.service import user_read  # noqa: PLC0415 - one direction at import

    return AuthResult(**tokens.model_dump(), user=user_read(user, memberships))


async def _store_pending_secret(
    session: AsyncSession, user: User, *, settings: Settings, now: datetime
) -> MfaEnrolmentStart:
    """Create a secret that is not a second factor until a code from it is confirmed."""
    row = await repository.mfa_by_user(session, user.id)
    if row is not None and row.confirmed_at is not None:
        raise MfaAlreadyEnrolled()
    secret = pyotp.random_base32()
    await repository.save_pending_mfa_secret(
        session,
        user.id,
        secret_ciphertext=encrypt_text(secret, key=settings.mfa_secret_key),
        now=now,
    )
    return MfaEnrolmentStart(secret=secret, otpauth_uri=_otpauth_uri(secret, user.email))


async def start_enrolment_from_challenge(
    session: AsyncSession, *, challenge_token: str, settings: Settings, now: datetime
) -> MfaEnrolmentStart:
    """Begin enrolment for a sign-in that was told a second factor is required."""
    user = await _active_user(
        session, _user_from_challenge(challenge_token, expected_type=MFA_ENROL_TYPE, settings=settings)
    )
    return await _store_pending_secret(session, user, settings=settings, now=now)


async def _confirm_secret(
    session: AsyncSession, user: User, row: UserMfa, *, code: str, settings: Settings, now: datetime
) -> list[str]:
    """Accept the first code, store ten recovery codes, and return them in plaintext."""
    if row.confirmed_at is not None:
        raise MfaAlreadyEnrolled()
    secret = decrypt_text(row.secret_ciphertext, key=settings.mfa_secret_key)
    step = accepted_totp_step(secret, code, now=now, last_used_step=None)
    await repository.confirm_mfa(session, user.id, at=now, step=step)
    codes = [_new_recovery_code() for _ in range(RECOVERY_CODE_COUNT)]
    await repository.replace_recovery_codes(
        session, user.id, [hash_password(code_text) for code_text in codes]
    )
    await _audit(session, actor=user, action="mfa.enrolled", now=now, summary="Enrolled an authenticator")
    return codes


async def confirm_enrolment_from_challenge(
    session: AsyncSession,
    *,
    challenge_token: str,
    code: str,
    memberships_for: MembershipLookup,
    settings: Settings,
    now: datetime,
    caller: str,
) -> MfaEnrolmentConfirmed:
    """Confirm the authenticator and sign in. The recovery codes are in this response only."""
    user_id = await _limited_challenge_user(
        challenge_token, expected_type=MFA_ENROL_TYPE, settings=settings, caller=caller
    )
    user = await _active_user(session, user_id)
    row = await repository.mfa_by_user(session, user.id)
    if row is None:
        raise MfaNotEnrolled()
    codes = await _confirm_secret(session, user, row, code=code, settings=settings, now=now)
    memberships = await memberships_for(session, user.id)
    signed_in = await _issue_session(
        session, user, settings=settings, now=now, memberships=memberships, count_as_login=True
    )
    return MfaEnrolmentConfirmed(**signed_in.model_dump(), recovery_codes=codes)


async def _spend_recovery_code(
    session: AsyncSession, user_id: uuid.UUID, presented: str, *, now: datetime
) -> bool:
    """Mark one matching unused recovery code used. False when none matches."""
    normalized = presented.strip().lower().replace(" ", "")
    for stored in await repository.unused_recovery_codes(session, user_id):
        if verify_password(stored.code_hash, normalized):
            await repository.mark_recovery_code_used(session, stored.id, at=now)
            return True
    return False


async def verify_challenge(
    session: AsyncSession,
    *,
    challenge_token: str,
    code: str | None,
    recovery_code: str | None,
    memberships_for: MembershipLookup,
    settings: Settings,
    now: datetime,
    caller: str,
) -> AuthResult:
    """Turn a challenge plus a current code into a session.

    A recovery code works once. A TOTP code whose step was already accepted is
    refused, even when it is still inside the one-step window.
    """
    if (code is None) == (recovery_code is None):
        raise InvalidMfaCode()
    user_id = await _limited_challenge_user(
        challenge_token, expected_type=MFA_CHALLENGE_TYPE, settings=settings, caller=caller
    )
    user = await _active_user(session, user_id)
    row = await repository.mfa_by_user(session, user.id)
    if row is None or row.confirmed_at is None:
        raise MfaNotEnrolled()
    if recovery_code is not None:
        if not await _spend_recovery_code(session, user.id, recovery_code, now=now):
            raise InvalidMfaCode()
        await _audit(
            session,
            actor=user,
            action="mfa.recovery_code_used",
            now=now,
            summary="Signed in with a recovery code",
        )
    else:
        secret = decrypt_text(row.secret_ciphertext, key=settings.mfa_secret_key)
        step = accepted_totp_step(secret, code or "", now=now, last_used_step=row.last_used_step)
        await repository.set_mfa_last_used_step(session, user.id, step)
    memberships = await memberships_for(session, user.id)
    return await _issue_session(
        session, user, settings=settings, now=now, memberships=memberships, count_as_login=True
    )


async def read_status(session: AsyncSession, *, user_id: uuid.UUID, is_platform_admin: bool) -> MfaStatusRead:
    """What `/me/mfa` shows: enrolled or not, and why a second factor is required."""
    flags = await tenancy.staff_mfa_flags(session, user_id)
    reason = mfa_required_reason(
        is_platform_admin=is_platform_admin,
        memberships=[MfaMembership(role=role, org_requires_staff_mfa=required) for role, required in flags],
    )
    row = await repository.mfa_by_user(session, user_id)
    enabled = row is not None and row.confirmed_at is not None
    remaining = await repository.count_unused_recovery_codes(session, user_id) if enabled else 0
    return MfaStatusRead(
        enabled=enabled,
        required=reason is not None,
        required_reason=reason,
        recovery_codes_remaining=remaining,
    )


async def start_enrolment_for_user(
    session: AsyncSession, *, user_id: uuid.UUID, settings: Settings, now: datetime
) -> MfaEnrolmentStart:
    """Begin enrolment from an existing session. Anyone with a password may do this."""
    user = await repository.user_by_id(session, user_id)
    if user is None or user.status != "active":
        raise AccountSuspended()
    return await _store_pending_secret(session, user, settings=settings, now=now)


async def confirm_enrolment_for_user(
    session: AsyncSession, *, user_id: uuid.UUID, code: str, settings: Settings, now: datetime, caller: str
) -> MfaRecoveryCodesRead:
    """Confirm an authenticator started from `/me`. The codes are shown once."""
    await check(MFA_VERIFY, f"{user_id}:{caller}")
    user = await repository.user_by_id(session, user_id)
    if user is None or user.status != "active":
        raise AccountSuspended()
    row = await repository.mfa_by_user(session, user.id)
    if row is None:
        raise MfaNotEnrolled()
    codes = await _confirm_secret(session, user, row, code=code, settings=settings, now=now)
    return MfaRecoveryCodesRead(recovery_codes=codes)


async def _confirmed_row(session: AsyncSession, user: User) -> UserMfa:
    """The live authenticator, or `mfa_not_enrolled`."""
    row = await repository.mfa_by_user(session, user.id)
    if row is None or row.confirmed_at is None:
        raise MfaNotEnrolled()
    return row


async def regenerate_recovery_codes(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    code: str,
    settings: Settings,
    now: datetime,
    caller: str,
) -> MfaRecoveryCodesRead:
    """Replace every recovery code. The current authenticator code is required."""
    await check(MFA_VERIFY, f"{user_id}:{caller}")
    user = await repository.user_by_id(session, user_id)
    if user is None or user.status != "active":
        raise AccountSuspended()
    row = await _confirmed_row(session, user)
    secret = decrypt_text(row.secret_ciphertext, key=settings.mfa_secret_key)
    step = accepted_totp_step(secret, code, now=now, last_used_step=row.last_used_step)
    await repository.set_mfa_last_used_step(session, user.id, step)
    codes = [_new_recovery_code() for _ in range(RECOVERY_CODE_COUNT)]
    await repository.replace_recovery_codes(
        session, user.id, [hash_password(code_text) for code_text in codes]
    )
    await _audit(
        session,
        actor=user,
        action="mfa.recovery_codes_regenerated",
        now=now,
        summary="Regenerated recovery codes",
    )
    return MfaRecoveryCodesRead(recovery_codes=codes)


async def disable_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    code: str,
    settings: Settings,
    now: datetime,
    caller: str,
) -> None:
    """Remove the authenticator. Refused when policy still requires one, before the code is read."""
    await check(MFA_VERIFY, f"{user_id}:{caller}")
    user = await repository.user_by_id(session, user_id)
    if user is None or user.status != "active":
        raise AccountSuspended()
    flags = await tenancy.staff_mfa_flags(session, user.id)
    if (
        mfa_required_reason(
            is_platform_admin=user.is_platform_admin,
            memberships=[
                MfaMembership(role=role, org_requires_staff_mfa=required) for role, required in flags
            ],
        )
        is not None
    ):
        raise MfaRequiredByPolicy()
    row = await _confirmed_row(session, user)
    secret = decrypt_text(row.secret_ciphertext, key=settings.mfa_secret_key)
    accepted_totp_step(secret, code, now=now, last_used_step=row.last_used_step)
    await repository.delete_mfa(session, user.id)
    await _audit(session, actor=user, action="mfa.disabled", now=now, summary="Turned off the authenticator")


async def reset_for_support(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    actor_email: str,
    now: datetime,
) -> None:
    """Clear a lost authenticator. The person enrols again at their next sign-in."""
    user = await repository.user_by_id(session, user_id)
    if user is None:
        return
    row = await repository.mfa_by_user(session, user.id)
    if row is None or row.confirmed_at is None:
        raise MfaNotEnrolled()
    await repository.delete_mfa(session, user.id)
    await tenancy.record_audit(
        session,
        org_id=None,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        action="mfa.reset_by_admin",
        at=now,
        target_type="user",
        target_id=str(user.id),
        summary="Support cleared the authenticator",
    )
