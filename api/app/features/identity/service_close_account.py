"""Ending an account's sessions, and closing it for good."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import repository
from app.features.identity.errors import AccountNotFound, InvalidCredentials
from app.features.identity.models import User
from app.features.tenancy import service as tenancy

RETENTION_DAYS = 30  # the privacy policy's month; `service_erasure` erases on the same day


async def end_sessions(session: AsyncSession, user_id: uuid.UUID, *, now: datetime, reason: str) -> None:
    """Revoke every refresh chain this person holds. Deactivating an account
    has to end its sessions; the token check above ends its access."""
    await repository.revoke_all_chains_for_user(session, user_id=user_id, at=now, reason=reason)


async def close_account(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    password: str | None,
    confirm: str | None,
    now: datetime,
) -> None:
    """Close the signed-in account. The row stays; sign-in stops.

    A hard delete collides with every consultation, payment and membership
    that points at the person. Status `deleted` is what the token check
    already refuses. The password stays, so signing in within the month reopens the
    account (`reopen_if_within_retention`); the erasure job clears it.
    """
    from app.features.identity.tokens import verify_password

    user = await repository.user_by_id(session, user_id)
    if user is None:
        raise AccountNotFound()
    if user.password_hash:
        if not verify_password(user.password_hash, password or ""):
            raise InvalidCredentials()
    elif (confirm or "").strip().lower() != "delete":
        raise InvalidCredentials()
    user.status = "deleted"
    # Read by the scheduled erasure job (`identity/jobs.py`) to find every
    # account closed more than 30 days ago.
    user.closed_at = now
    await repository.revoke_all_chains_for_user(session, user_id=user_id, at=now, reason="account_closed")
    await tenancy.record_audit(
        session,
        org_id=None,
        actor_user_id=user.id,
        actor_email=user.email,
        action="account.closed",
        at=now,
        target_type="user",
        target_id=str(user.id),
        summary="Account closed by its owner",
    )


async def reopen_if_within_retention(session: AsyncSession, user: User, *, now: datetime) -> bool:
    """Bring a closed account back when its owner proves the password inside the month.

    False when the account is not closed, was erased, or the month has passed; the caller then
    refuses the sign-in as it does for any account that is not active.
    """
    if user.status != "deleted" or user.closed_at is None or user.erased_at is not None:
        return False
    if now - user.closed_at >= timedelta(days=RETENTION_DAYS):
        return False
    user.status = "active"
    user.closed_at = None
    await tenancy.record_audit(
        session,
        org_id=None,
        actor_user_id=user.id,
        actor_email=user.email,
        action="account.reopened",
        at=now,
        target_type="user",
        target_id=str(user.id),
        summary="Closed account reopened by signing in",
    )
    return True
