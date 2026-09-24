"""Setting, resetting and changing a password.

Split from `service.py` along the story rather than the file size: registering
and signing in are about who you are, and these are about the secret that
proves it. Every one of them ends every existing session, which is the thread
they share.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import repository
from app.features.identity.domain import WeakPassword, validate_password
from app.features.identity.errors import (
    InvalidCredentials,
    InvalidResetToken,
    WeakPasswordError,
)
from app.features.identity.tokens import hash_password, hash_token, new_token, verify_password
from app.features.notifications import service as notifications


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


async def confirm_password_reset(session: AsyncSession, *, token: str, password: str, now: datetime) -> None:
    try:
        validate_password(password)
    except WeakPassword as exc:
        raise WeakPasswordError(str(exc)) from exc
    record = await repository.reset_token_by_hash(session, hash_token(token))
    if record is None or record.used_at is not None or now >= record.expires_at:
        raise InvalidResetToken()
    user = await repository.user_by_id(session, record.user_id)
    if user is not None and user.password_login_disabled:
        # Defense in depth: `begin_password_reset` above never issues a
        # token for one of these accounts, but a token could in principle
        # reach here by another path (`service_invitations.py` also mints
        # reset tokens, for a roster admin's invite/resend — not yet checked
        # against this flag; see `docs/decisions-2026-09-24.md` item 2).
        raise InvalidResetToken()
    await repository.mark_reset_token_used(session, token_id=record.id, at=now)
    await repository.set_password_hash(session, record.user_id, hash_password(password))
    # A password change ends every existing session: whoever prompted the reset
    # may be holding one.
    await repository.revoke_all_chains_for_user(
        session, user_id=record.user_id, at=now, reason="password_reset"
    )


async def change_password(
    session: AsyncSession, *, user_id: uuid.UUID, current: str, new: str, now: datetime
) -> None:
    try:
        validate_password(new)
    except WeakPassword as exc:
        raise WeakPasswordError(str(exc)) from exc
    user = await repository.user_by_id(session, user_id)
    if user is None or not verify_password(user.password_hash, current):
        raise InvalidCredentials()
    await repository.set_password_hash(session, user_id, hash_password(new))
    await repository.revoke_all_chains_for_user(session, user_id=user_id, at=now, reason="password_change")
