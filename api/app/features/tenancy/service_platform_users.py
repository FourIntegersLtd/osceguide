"""The platform console: accounts, as the people who answer support see them.

Every mutation writes an audit row with no organisation, since none of these is an
organisation's act — "who did what to whose account" has to be answerable from the audit
log alone.

Accounts belong to `identity`; every read and write here goes through
`identity.service_platform`, never its table.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_wording import RELAYED_PASSWORD_NOTE
from app.core.auth import Principal
from app.features.identity import service as identity
from app.features.identity import service_close_account, service_mfa, service_passwords
from app.features.identity import service_invitations as invitations
from app.features.identity import service_platform as accounts
from app.features.tenancy import repository, repository_platform
from app.features.tenancy.errors import (
    CannotRevokeOwnConsoleAccess,
    InvitationPending,
    PasswordAlreadyChosen,
    PlatformAdminExists,
    UserNotFound,
)
from app.features.tenancy.schemas import (
    MembershipRead,
    PlatformAdminInviteRead,
    PlatformAuditRead,
    PlatformUserDetail,
    UpdatePlatformUser,
    UserSummary,
)
from app.features.tenancy.service_platform import platform_audit_read

_STAFF_CONSOLE_LABEL = "the OSCE Guide staff console"


def _user_summary(user: accounts.SupportUser) -> UserSummary:
    """Shape an account into the summary a support search result shows."""
    return UserSummary(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
        is_platform_admin=user.is_platform_admin,
        status=user.status,
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
    users, next_cursor = await accounts.search_users(
        session, query=query, limit=limit, cursor=cursor, platform_admin=platform_admin
    )
    return [_user_summary(user) for user in users], next_cursor


async def list_platform_admins(session: AsyncSession, *, limit: int = 100) -> list[UserSummary]:
    return [_user_summary(user) for user in await accounts.list_platform_admins(session, limit=limit)]


async def invite_platform_admin(
    session: AsyncSession, *, email: str, actor: Principal, now: datetime
) -> PlatformAdminInviteRead:
    """Grant the staff console by email.

    An unknown address is invited: an account without a password and an email carrying a
    link to choose one.
    """
    address = email.strip()
    ref = await identity.user_ref_by_email(session, address)
    invited = ref is None
    if ref is None:
        ref = await invitations.invite_user(
            session, email=address, name=address, invited_to=_STAFF_CONSOLE_LABEL, now=now
        )
    existing = await accounts.user_by_id(session, ref.id)
    if existing is None:
        raise UserNotFound()
    if existing.is_platform_admin:
        raise PlatformAdminExists()
    user = await set_platform_admin(session, ref.id, is_admin=True, actor=actor)
    return PlatformAdminInviteRead(user=user, invited=invited)


async def set_platform_admin(
    session: AsyncSession, user_id: uuid.UUID, *, is_admin: bool, actor: Principal
) -> UserSummary:
    """Grant or revoke the console itself. Audited without an organisation, since this is a
    platform act.

    Nobody revokes their own access: the actor is by construction a platform admin, so
    this is also what keeps the console from ever being left with none.
    """
    if not is_admin and user_id == actor.user_id:
        raise CannotRevokeOwnConsoleAccess()
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
    """Fetch an account, or refuse if no account exists with that id."""
    user = await accounts.user_by_id(session, user_id)
    if user is None:
        raise UserNotFound()
    return user


async def read_user(session: AsyncSession, user_id: uuid.UUID) -> PlatformUserDetail:
    """The full account detail the platform console shows, memberships included."""
    user = await _require(session, user_id)
    memberships = [
        MembershipRead(
            id=membership.id,
            user_id=membership.user_id,
            email=user.email,
            role=membership.role,
            product_surface=membership.product_surface,
            status=membership.status,
            revoked_at=membership.revoked_at,
        )
        for membership in await repository.memberships_for_user(session, user_id)
    ]
    legacy_ids = await accounts.consumer_legacy_ids(session, user_id)
    return PlatformUserDetail(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
        is_platform_admin=user.is_platform_admin,
        status=user.status,
        must_change_password=user.must_change_password,
        last_login_at=user.last_login_at,
        exam_code=user.exam_code,
        exam_date=user.exam_date,
        needs_extra_time=user.needs_extra_time,
        custom_reading_seconds=user.custom_reading_seconds,
        custom_simulation_seconds=user.custom_simulation_seconds,
        consumer_role=user.consumer_role,
        legacy_consumer_ids=legacy_ids,
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

    Deactivating ends the person's sessions here and now: every refresh chain is revoked,
    and `core.auth` refuses their access token on its next request.
    """
    before = await _require(session, user_id)
    values = changes.model_dump(exclude_unset=True)
    if values:
        if await accounts.update_user(session, user_id, **values) is None:
            raise UserNotFound()
        action = "user.updated"
        status = values.get("status")
        if status == "deactivated" and before.status != "deactivated":
            await service_close_account.end_sessions(session, user_id, now=now, reason="deactivated_by_admin")
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
    """Send this account a password reset email, on the console's behalf."""
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


async def reissue_temporary_password(
    session: AsyncSession, user_id: uuid.UUID, *, password: str, actor: Principal, now: datetime
) -> None:
    """Hand an account that has not yet changed its relayed password a new one."""
    user = await _require(session, user_id)
    if not await invitations.reissue_temporary_password(session, user_id=user_id, password=password, now=now):
        ref = await identity.user_ref_by_email(session, user.email)
        raise InvitationPending() if ref is not None and ref.invitation_pending else PasswordAlreadyChosen()
    await repository.write_audit(
        session,
        org_id=None,
        actor_user_id=actor.user_id,
        actor_email=actor.email,
        action="user.temporary_password_reissued",
        target_type="user",
        target_id=str(user_id),
        summary=f"{user.email}{RELAYED_PASSWORD_NOTE}",
    )


async def reset_user_mfa(
    session: AsyncSession, user_id: uuid.UUID, *, actor: Principal, now: datetime
) -> None:
    """Clear a lost authenticator so the person can enrol again at the next sign-in."""
    await _require(session, user_id)
    await service_mfa.reset_for_support(
        session,
        user_id=user_id,
        actor_user_id=actor.user_id,
        actor_email=actor.email,
        now=now,
    )


async def list_audit_about_user(
    session: AsyncSession, user_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[PlatformAuditRead], str | None]:
    """What was done to this account, and what it did — the history tab."""
    await _require(session, user_id)
    entries, next_cursor = await repository_platform.list_audit_about_user(
        session, user_id, limit=limit, cursor=cursor
    )
    return [platform_audit_read(entry) for entry in entries], next_cursor
