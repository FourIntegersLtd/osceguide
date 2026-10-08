"""Ending an account's sessions, and closing it for good."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import repository
from app.features.identity.errors import AccountNotFound, InvalidCredentials


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
    already refuses, and the password is cleared so it cannot be reused.
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
    user.password_hash = None
    # Read by the scheduled erasure job (`identity/jobs.py`) to find every
    # account closed more than 30 days ago.
    user.closed_at = now
    await repository.revoke_all_chains_for_user(session, user_id=user_id, at=now, reason="account_closed")
