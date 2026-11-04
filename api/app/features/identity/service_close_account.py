"""Ending an account's sessions, and closing it for good."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.account_status import forget_status
from app.features.identity import repository
from app.features.identity.errors import AccountNotFound, InvalidCredentials
from app.features.identity.models import User
from app.features.notifications import service as notifications
from app.features.tenancy import service as tenancy

RETENTION_DAYS = 30  # the privacy policy's month; `service_erasure` erases on the same day


async def end_sessions(session: AsyncSession, user_id: uuid.UUID, *, now: datetime, reason: str) -> None:
    """Revoke every refresh chain this person holds. Deactivating an account
    has to end its sessions; the token check above ends its access."""
    await repository.revoke_all_chains_for_user(session, user_id=user_id, at=now, reason=reason)


async def _audit_account(session: AsyncSession, user: User, action: str, now: datetime, summary: str) -> None:
    """One platform-level audit row about the account, acted by its owner."""
    await tenancy.record_audit(
        session,
        org_id=None,
        actor_user_id=user.id,
        actor_email=user.email,
        action=action,
        at=now,
        target_type="user",
        target_id=str(user.id),
        summary=summary,
    )


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
        if not await verify_password(user.password_hash, password or ""):
            raise InvalidCredentials()
    elif (confirm or "").strip().lower() != "delete":
        raise InvalidCredentials()
    user.status = "deleted"
    forget_status(session, user_id)
    # Read by the scheduled erasure job (`identity/jobs.py`) to find every
    # account closed more than 30 days ago.
    user.closed_at = now
    await repository.revoke_all_chains_for_user(session, user_id=user_id, at=now, reason="account_closed")
    await _audit_account(session, user, "account.closed", now, "Account closed by its owner")


async def can_reopen(session: AsyncSession, user: User, *, now: datetime) -> bool:
    """Whether a complete sign-in would bring this closed account back: closed by its owner,
    not erased, and inside the month. Changes nothing, so a sign-in still waiting on a second
    factor can be let through to its challenge without undoing the closure yet."""
    if user.status != "deleted" or user.closed_at is None or user.erased_at is not None:
        return False
    if now - user.closed_at >= timedelta(days=RETENTION_DAYS):
        return False
    # Only the owner's own closing is undone by signing in; any other closure stays closed.
    return await tenancy.acted_on_themselves(session, action="account.closed", user_id=user.id)


async def reopen_if_within_retention(session: AsyncSession, user: User, *, now: datetime) -> bool:
    """Bring a closed account back once its owner has completed sign-in inside the month.

    Called only where a session is minted (after any second factor), never on a password alone:
    reopening reverses the closure and cancels the erasure. False when `can_reopen` is; the
    caller then refuses the sign-in as it does for any account that is not active.
    """
    if not await can_reopen(session, user, now=now):
        return False
    user.status = "active"
    forget_status(session, user.id)
    user.closed_at = None
    await _audit_account(session, user, "account.reopened", now, "Closed account reopened by signing in")
    await notifications.enqueue_email(
        session,
        recipient=user.email,
        subject="Your OSCE Guide account is open again",
        template_key="account_reopened",
        payload={},
        idempotency_key=f"account_reopened:{user.id}:{int(now.timestamp())}",
    )
    return True
