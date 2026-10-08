"""The platform console's account routes. Every one of them is `PlatformAdmin`."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.tenancy import PlatformAdmin
from app.features.tenancy import errors, schemas, service_platform_users

router = APIRouter(tags=["tenancy"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/platform/users",
    response_model=Page[schemas.UserSummary],
    responses=error_responses(Forbidden),
)
async def search_users(
    admin: PlatformAdmin,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    q: Annotated[str | None, Query(description="Part of an email address")] = None,
    platform_admin: Annotated[
        bool | None, Query(description="Only accounts that may (or may not) use this console")
    ] = None,
) -> Page[schemas.UserSummary]:
    """Find an account by email, for the people who answer "I cannot sign in"."""
    _ = admin
    users, next_cursor = await service_platform_users.search_users(
        session, query=q, limit=page.limit, cursor=page.cursor, platform_admin=platform_admin
    )
    return Page(items=users, next_cursor=next_cursor)


@router.get(
    "/platform/admins",
    response_model=list[schemas.UserSummary],
    responses=error_responses(Forbidden),
)
async def list_platform_admins(admin: PlatformAdmin, session: Session) -> list[schemas.UserSummary]:
    """Everyone who may use this console."""
    _ = admin
    return await service_platform_users.list_platform_admins(session)


@router.post(
    "/platform/admins",
    response_model=schemas.PlatformAdminInviteRead,
    responses=error_responses(Forbidden, errors.PlatformAdminExists),
)
async def invite_platform_admin(
    body: schemas.InvitePlatformAdmin,
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.PlatformAdminInviteRead:
    """Add somebody to the platform team by email.

    No password passes through this app. A new address is invited and emailed a
    link to choose one; an existing account is granted the console immediately.
    """
    return await service_platform_users.invite_platform_admin(
        session, email=body.email, name=body.name, actor=admin, now=clock.now()
    )


@router.get(
    "/platform/users/{user_id}",
    response_model=schemas.PlatformUserDetail,
    responses=error_responses(Forbidden, errors.UserNotFound),
)
async def read_user(user_id: uuid.UUID, admin: PlatformAdmin, session: Session) -> schemas.PlatformUserDetail:
    """The support view of one account: flags, last sign-in, memberships."""
    _ = admin
    return await service_platform_users.read_user(session, user_id)


@router.patch(
    "/platform/users/{user_id}",
    response_model=schemas.PlatformUserDetail,
    responses=error_responses(Forbidden, errors.UserNotFound, errors.LastAdministrator),
)
async def update_user(
    user_id: uuid.UUID,
    body: schemas.UpdatePlatformUser,
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.PlatformUserDetail:
    """Correct a name or exam, or deactivate the account — which ends its
    sessions and any consultation it has open now, not at the next refresh. Refused
    for the only active administrator of an organisation."""
    return await service_platform_users.update_user(
        session, user_id, changes=body, actor=admin, now=clock.now()
    )


@router.put(
    "/platform/users/{user_id}/platform-admin",
    response_model=schemas.UserSummary,
    responses=error_responses(Forbidden, errors.UserNotFound, errors.CannotRevokeOwnConsoleAccess),
)
async def set_platform_admin(
    user_id: uuid.UUID,
    body: schemas.SetPlatformAdmin,
    admin: PlatformAdmin,
    session: Session,
) -> schemas.UserSummary:
    """Grant or revoke the console itself. One route, because they are one
    decision and two would invite one of them to be forgotten."""
    return await service_platform_users.set_platform_admin(
        session, user_id, is_admin=body.is_platform_admin, actor=admin
    )


@router.post(
    "/platform/users/{user_id}/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Forbidden, errors.UserNotFound, errors.PasswordResetNotSent),
)
async def reset_user_password(
    user_id: uuid.UUID, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> Response:
    """Send the person a link to choose a new password."""
    await service_platform_users.trigger_password_reset(session, user_id, actor=admin, now=clock.now())
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/platform/users/{user_id}/temporary-password",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(
        Forbidden,
        errors.UserNotFound,
        errors.PasswordAlreadyChosen,
        errors.InvitationPending,
        errors.WeakPasswordError,
    ),
)
async def reissue_temporary_password(
    user_id: uuid.UUID,
    body: schemas.ReissueTemporaryPassword,
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
) -> Response:
    """Replace a relayed password that was lost, for an account that has not yet
    changed it. Ends the account's sessions. Refused once they chose their own."""
    await service_platform_users.reissue_temporary_password(
        session, user_id, password=body.temporary_password, actor=admin, now=clock.now()
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Clear a lost authenticator. The person enrols again the next time they sign in.
@router.post(
    "/platform/users/{user_id}/reset-mfa",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Forbidden, errors.UserNotFound, errors.MfaNotEnrolled),
)
async def reset_user_mfa(
    user_id: uuid.UUID, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> Response:
    await service_platform_users.reset_user_mfa(session, user_id, actor=admin, now=clock.now())
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/platform/users/{user_id}/audit",
    response_model=Page[schemas.PlatformAuditRead],
    responses=error_responses(Forbidden, errors.UserNotFound),
)
async def list_user_audit_for_support(
    user_id: uuid.UUID,
    admin: PlatformAdmin,
    session: Session,
    page: Annotated[CursorParams, Depends()],
) -> Page[schemas.PlatformAuditRead]:
    """Everything done to this account and everything it did, newest first."""
    _ = admin
    audit_entries, next_cursor = await service_platform_users.list_audit_about_user(
        session, user_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=audit_entries, next_cursor=next_cursor)
