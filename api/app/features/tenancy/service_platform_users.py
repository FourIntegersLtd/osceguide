"""The platform console: accounts, as the people who answer support see them.

Split from `service_platform.py` at the file cap. That module is about
organisations; this one is about a person — finding them, reading what the
list row omits, correcting a field, sending a reset, granting the console.
Every mutation writes an audit row with no organisation, because none of these
is an organisation's act: it is the platform's, and "who did what to whose
account" has to be answerable from the audit log alone.

Accounts belong to `identity`, which sits below this slice; every read and
write here goes through `identity.service_platform`, never its table.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.identity import service as identity
from app.features.identity import service_passwords
from app.features.identity import service_platform as accounts
from app.features.tenancy import repository, repository_platform
from app.features.tenancy.errors import UserNotFound
from app.features.tenancy.schemas import (
    MembershipRead,
    PlatformAuditRead,
    PlatformUserDetail,
    UpdatePlatformUser,
    UserSummary,
)
from app.features.tenancy.service_platform_audit import platform_audit_read


def _user_summary(user: accounts.SupportUser) -> UserSummary:
    return UserSummary(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
        is_platform_admin=user.is_platform_admin,
    )


async def search_users(
    session: AsyncSession,
    *,
    query: str | None,
    limit: int,
    cursor: dict[str, Any] | None,
    platform_admin: bool | None = None,
) -> tuple[list[UserSummary], str | None]:
    """Find an account by email, for the people who answer support."""
    rows, next_cursor = await accounts.search_users(
        session, query=query, limit=limit, cursor=cursor, platform_admin=platform_admin
    )
    return [_user_summary(row) for row in rows], next_cursor


async def list_platform_admins(session: AsyncSession, *, limit: int = 100) -> list[UserSummary]:
    return [_user_summary(row) for row in await accounts.list_platform_admins(session, limit=limit)]


async def set_platform_admin(
    session: AsyncSession, user_id: uuid.UUID, *, is_admin: bool, actor: Principal
) -> UserSummary:
    """Grant or revoke the console itself.

    Audited without an organisation: this is a platform act, and the audit log
    is where "who made whom an administrator" has to be answerable from.
    """
    user = await identity.set_platform_admin(session, user_id, is_admin=is_admin)
    await repository.write_audit(
        session,
        org_id=None,
        actor_user_id=actor.user_id,
        actor_email=actor.email,
        action="platform_admin.granted" if is_admin else "platform_admin.revoked",
        target_type="user",
        target_id=str(user_id),
        summary=user.email,
    )
    return _user_summary(await _require(session, user_id))


async def _require(session: AsyncSession, user_id: uuid.UUID) -> accounts.SupportUser:
    user = await accounts.user_by_id(session, user_id)
    if user is None:
        raise UserNotFound()
    return user


async def read_user(session: AsyncSession, user_id: uuid.UUID) -> PlatformUserDetail:
    user = await _require(session, user_id)
    memberships = [
        MembershipRead(
            id=row.id,
            user_id=row.user_id,
            email=user.email,
            role=row.role,
            product_surface=row.product_surface,
            status=row.status,
            revoked_at=row.revoked_at,
        )
        for row in await repository.memberships_for_user(session, user_id)
    ]
    return PlatformUserDetail(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
        is_platform_admin=user.is_platform_admin,
        must_change_password=user.must_change_password,
        last_login_at=user.last_login_at,
        exam_code=user.exam_code,
        memberships=memberships,
    )


async def update_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    changes: UpdatePlatformUser,
    actor: Principal,
    now: datetime,
) -> PlatformUserDetail:
    """Correct a field, or deactivate the account.

    Deactivating ends the person's sessions here and now: every refresh chain
    is revoked, and `core.auth` refuses their access token on its next
    request. Before this the status was written and nothing read it until the
    next refresh, so a deactivated account kept working for up to fifteen
    minutes — and longer if it never refreshed.
    """
    before = await _require(session, user_id)
    values = changes.model_dump(exclude_unset=True)
    if values:
        if await accounts.update_user(session, user_id, **values) is None:
            raise UserNotFound()
        action = "user.updated"
        status = values.get("status")
        if status == "deactivated" and before.status != "deactivated":
            await identity.end_sessions(session, user_id, now=now, reason="deactivated_by_admin")
            action = "user.deactivated"
        elif status == "active" and before.status != "active":
            action = "user.reactivated"
        await repository.write_audit(
            session,
            org_id=None,
            actor_user_id=actor.user_id,
            actor_email=actor.email,
            action=action,
            target_type="user",
            target_id=str(user_id),
            summary=", ".join(f"{key}={value}" for key, value in sorted(values.items())),
        )
    return await read_user(session, user_id)


async def trigger_password_reset(
    session: AsyncSession, user_id: uuid.UUID, *, actor: Principal, now: datetime
) -> None:
    user = await _require(session, user_id)
    await service_passwords.begin_password_reset(session, email=user.email, now=now)
    await repository.write_audit(
        session,
        org_id=None,
        actor_user_id=actor.user_id,
        actor_email=actor.email,
        action="user.password_reset_sent",
        target_type="user",
        target_id=str(user_id),
        summary=user.email,
    )


async def list_audit_about_user(
    session: AsyncSession, user_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[PlatformAuditRead], str | None]:
    """What was done to this account, and what it did — the history tab."""
    await _require(session, user_id)
    rows, next_cursor = await repository_platform.list_audit_about_user(
        session, user_id, limit=limit, cursor=cursor
    )
    return [platform_audit_read(row) for row in rows], next_cursor
