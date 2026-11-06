"""Setting, resetting and changing a password.

Every one of them ends every existing session.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.memberships import MembershipLookup
from app.core.settings import Settings
from app.features.identity import repository, service_sessions
from app.features.identity.domain import WeakPassword, validate_password
from app.features.identity.errors import (
    AccountNotFound,
    AccountSuspended,
    InvalidCredentials,
    InvalidResetToken,
    PasswordLoginDisabled,
    PasswordNotSet,
    WeakPasswordError,
)
from app.features.identity.schemas import TokenPair
from app.features.identity.tokens import hash_password, hash_token, new_token, verify_password
from app.features.notifications import service as notifications
from app.features.tenancy import service as tenancy


async def begin_password_reset(
    session: AsyncSession, *, email: str, now: datetime, ttl_minutes: int = 60
) -> str | None:
    """Returns the raw token when the address exists, else None.

    The route answers 202 either way: telling a caller whether an address is
    registered is the whole of an account-enumeration attack.

    The email is queued in this transaction, beside the token that makes it
    valid, so neither can exist without the other.
    """
    user = await repository.user_by_email(session, email)
    if user is None:
        return None
    if user.password_login_disabled:
        # Same non-answer an unknown address gets — sending a reset link
        # would hand an SSO-only account a password to sign in with, and a
        # distinct response here would leak which addresses are SSO-only.
        return None
    raw, token_hash = new_token()
    await repository.create_reset_token(
        session, user_id=user.id, token_hash=token_hash, expires_at=now + timedelta(minutes=ttl_minutes)
    )
    await notifications.enqueue_email(
        session,
        recipient=user.email,
        subject="Reset your password",
        template_key="password_reset",
        payload={"token": raw},
        idempotency_key=f"password_reset:{token_hash}",
    )
    return raw


async def confirm_password_reset(session: AsyncSession, *, token: str, password: str, now: datetime) -> str:
    """Redeem a reset link for a new password, refusing `invalid_reset_token`
    for one that is unknown, spent, expired, or belongs to an account whose
    password sign-in an SSO arrangement has since disabled. Ends every
    existing session on success, since a reset is itself a sign that one
    of them may not be the account's owner. Returns the account's email, which
    the holder of the emailed token already controls."""
    try:
        validate_password(password)
    except WeakPassword as exc:
        raise WeakPasswordError(str(exc)) from exc
    record = await repository.reset_token_by_hash(session, hash_token(token))
    if record is None or record.used_at is not None or now >= record.expires_at:
        raise InvalidResetToken()
    user = await repository.user_by_id(session, record.user_id)
    if user is None or user.password_login_disabled:
        # Defense in depth: `begin_password_reset` above never issues a
        # token for one of these accounts, but a token could in principle
        # reach here by another path (`service_invitations.py` also mints
        # reset tokens, for a roster admin's invite/resend, and refuses these
        # accounts too — SEC-011).
        raise InvalidResetToken()
    await repository.mark_reset_token_used(session, token_id=record.id, at=now)
    await repository.set_password_hash(session, record.user_id, await hash_password(password))
    # A password change ends every existing session: whoever prompted the reset
    # may be holding one.
    await repository.revoke_all_chains_for_user(
        session, user_id=record.user_id, at=now, reason="password_reset"
    )
    return user.email


async def change_password(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    current: str,
    new: str,
    memberships_for: MembershipLookup,
    settings: Settings,
    now: datetime,
) -> TokenPair:
    """Set a new password once the current one is proved, refusing
    `invalid_credentials` for an unknown account or a wrong current
    password. Ends every session, so a credential a thief also knows does
    not survive the owner locking them out, and answers with a fresh pair so
    the device that made the change stays signed in.

    An account whose organisation signs it in is refused
    `password_login_disabled`, and one with no password yet
    `password_not_set`, rather than an `invalid_credentials` no current
    password could ever pass. A suspended account is refused
    `account_suspended` after the password, as sign-in refuses it, so a
    token minted before the suspension cannot buy a fresh pair here."""
    try:
        validate_password(new)
    except WeakPassword as exc:
        raise WeakPasswordError(str(exc)) from exc
    user = await repository.user_by_id(session, user_id)
    if user is None:
        raise AccountNotFound()
    if user.password_login_disabled:
        raise PasswordLoginDisabled()
    if user.password_hash is None:
        raise PasswordNotSet()
    if not await verify_password(user.password_hash, current):
        raise InvalidCredentials()
    if user.status != "active":
        raise AccountSuspended()
    await repository.set_password_hash(session, user_id, await hash_password(new))
    await repository.revoke_all_chains_for_user(session, user_id=user_id, at=now, reason="password_change")
    # `set_password_hash` also cleared `must_change_password`; the new token is
    # minted from the row as it now stands.
    await session.refresh(user)
    memberships = await memberships_for(session, user.id)
    return await service_sessions.issue(session, user, settings=settings, now=now, memberships=memberships)


async def invitation_organisation_name(session: AsyncSession, *, token: str, now: datetime) -> str:
    """The name of the organisation behind a live invitation token.

    Refuses `invalid_reset_token` for every other case alike (unknown, spent, expired, a plain
    reset link that names no organisation, an account SSO has since taken the password from), so
    the answer tells a token-tester nothing `confirm_password_reset` would not. Writes nothing.
    """
    record = await repository.reset_token_by_hash(session, hash_token(token))
    if record is None or record.used_at is not None or now >= record.expires_at:
        raise InvalidResetToken()
    if record.organization_id is None:
        raise InvalidResetToken()
    user = await repository.user_by_id(session, record.user_id)
    if user is None or user.password_login_disabled:
        raise InvalidResetToken()
    org = await tenancy.org_ref_by_id(session, record.organization_id)
    if org is None:
        raise InvalidResetToken()
    return org.name
