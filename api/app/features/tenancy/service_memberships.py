"""Who is in an organisation, and with what role.

Split from `service.py` along the aggregate: that module is about the
organisation itself, this one about the people in it. Nothing could create a
membership through the API for the whole build — an organisation could be
provisioned and then never given a single member — so these routes are the
half that makes the institutional product usable.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.identity import service as identity
from app.features.tenancy import domain, repository
from app.features.tenancy.errors import MembershipExists, MembershipNotFound, UserNotFound
from app.features.tenancy.schemas import MembershipRead


async def list_memberships(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[MembershipRead], str | None]:
    rows, next_cursor = await repository.list_memberships(session, org_id, limit=limit, cursor=cursor)
    return [_membership_read(r) for r in rows], next_cursor


async def add_membership(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    email: str,
    role: str,
    product_surface: str | None,
    actor: Principal,
) -> MembershipRead:
    """Put somebody in an organisation.

    By email, because that is what an administrator knows. Nothing could create
    a membership through the API for a while: an organisation could be
    provisioned and then never given a single member.
    """
    user = await identity.user_ref_by_email(session, email)
    if user is None:
        raise UserNotFound()
    user_id = user.id
    if await repository.membership_for_user_in_org(session, org_id, user_id, role=role) is not None:
        raise MembershipExists()
    membership = await repository.add_membership(
        session, org_id=org_id, user_id=user_id, role=role, product_surface=product_surface
    )
    await repository.write_audit(
        session,
        org_id=org_id,
        actor_user_id=actor.user_id,
        actor_email=actor.email,
        action="membership.added",
        target_type="membership",
        target_id=str(user_id),
        summary=f"Granted {role} to {email}",
    )
    return _membership_read(membership, email=user.email)


async def change_membership_role(
    session: AsyncSession, org_id: uuid.UUID, membership_id: uuid.UUID, *, role: str, actor: Principal
) -> MembershipRead:
    membership = await _require_membership(session, org_id, membership_id)
    await repository.set_membership_role(session, org_id, membership_id, role=role)
    await repository.write_audit(
        session,
        org_id=org_id,
        actor_user_id=actor.user_id,
        actor_email=actor.email,
        action="membership.role_changed",
        target_type="membership",
        target_id=str(membership_id),
        summary=f"{membership.role} to {role}",
    )
    return _membership_read(await _require_membership(session, org_id, membership_id))


async def set_membership_revoked(
    session: AsyncSession,
    org_id: uuid.UUID,
    membership_id: uuid.UUID,
    *,
    revoked: bool,
    actor: Principal,
    now: datetime,
) -> MembershipRead:
    """Revoke or restore someone's place in an organisation.

    Revocation is a timestamp rather than a delete, so "why could they do
    that?" stays answerable. It bites on the member's next token: the access
    token lives fifteen minutes and its refresh reads memberships again.
    """
    await _require_membership(session, org_id, membership_id)
    await repository.set_membership_revoked(session, org_id, membership_id, at=now if revoked else None)
    await repository.write_audit(
        session,
        org_id=org_id,
        actor_user_id=actor.user_id,
        actor_email=actor.email,
        action="membership.revoked" if revoked else "membership.restored",
        target_type="membership",
        target_id=str(membership_id),
    )
    return _membership_read(await _require_membership(session, org_id, membership_id))


async def _require_membership(session: AsyncSession, org_id: uuid.UUID, membership_id: uuid.UUID) -> Any:
    row = await repository.membership_by_id(session, org_id, membership_id)
    if row is None:
        raise MembershipNotFound()
    return row


def _membership_read(row: Any, *, email: str | None = None) -> MembershipRead:
    return MembershipRead(
        id=row.id,
        user_id=row.user_id,
        email=email,
        role=row.role,
        product_surface=row.product_surface,
        status=row.status,
        revoked_at=row.revoked_at,
    )


async def count_staff(session: AsyncSession, org_id: uuid.UUID) -> int:
    """Admins and supervisors: the people who can run a sitting.

    Trainees are members too, and counting them here would tell an organisation
    its team was staffed when nobody could supervise anything.
    """
    roles = sorted(domain.ORG_ADMIN_ROLES | {domain.ASSIGNED_STAFF_ROLE})
    return await repository.count_memberships(session, org_id, roles=roles)
