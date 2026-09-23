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
from app.features.identity import service_invitations as invitations
from app.features.tenancy import domain, repository
from app.features.tenancy.errors import MembershipExists, MembershipNotFound, OrgNotFound
from app.features.tenancy.schemas import MembershipRead


async def list_memberships(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[MembershipRead], str | None]:
    rows, next_cursor = await repository.list_memberships(session, org_id, limit=limit, cursor=cursor)
    # The addresses are read for the page instead of being left null. A team
    # list without an email can only show the front of a user id, which is a
    # uuid printed as if it were a name; the one join is the whole of the fix.
    people = await identity.user_refs_by_ids(session, [row.user_id for row in rows])
    return [
        _membership_read(row, email=people[row.user_id].email if row.user_id in people else None)
        for row in rows
    ], next_cursor


async def add_membership(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    email: str,
    role: str,
    product_surface: str | None,
    actor: Principal,
    now: datetime,
) -> MembershipRead:
    """Put somebody in an organisation.

    By email, because that is what an administrator knows. Nothing could create
    a membership through the API for a while: an organisation could be
    provisioned and then never given a single member.

    An address with no account is invited rather than refused: the account is
    created without a password and the person is emailed a link to choose one.
    Refusing meant every tutor had to register unprompted before an
    administrator could name them, and nobody tells a tutor to do that.
    """
    user = await identity.user_ref_by_email(session, email)
    invited = user is None
    if user is None:
        org = await repository.organization_by_id(session, org_id)
        if org is None:
            raise OrgNotFound()
        user = await invitations.invite_user(session, email=email, name=email, invited_to=org.name, now=now)
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
        summary=f"Granted {role} to {email}" + (" (invited)" if invited else ""),
    )
    return _membership_read(membership, email=user.email, invited=invited)


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
    return await _read_with_email(session, await _require_membership(session, org_id, membership_id))


async def _read_with_email(session: AsyncSession, row: Any) -> MembershipRead:
    """A membership answered the way the list answers it.

    The write routes used to return the row with no address on it, so a screen
    that had just changed a role or revoked one lost the email it was already
    showing. `add_membership` does not need this — it looked the person up by
    address to do the job at all.
    """
    people = await identity.user_refs_by_ids(session, [row.user_id])
    return _membership_read(row, email=people[row.user_id].email if row.user_id in people else None)


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
    return await _read_with_email(session, await _require_membership(session, org_id, membership_id))


async def _require_membership(session: AsyncSession, org_id: uuid.UUID, membership_id: uuid.UUID) -> Any:
    row = await repository.membership_by_id(session, org_id, membership_id)
    if row is None:
        raise MembershipNotFound()
    return row


def _membership_read(row: Any, *, email: str | None = None, invited: bool = False) -> MembershipRead:
    return MembershipRead(
        id=row.id,
        user_id=row.user_id,
        email=email,
        role=row.role,
        product_surface=row.product_surface,
        status=row.status,
        revoked_at=row.revoked_at,
        invited=invited,
    )


async def count_staff(session: AsyncSession, org_id: uuid.UUID) -> int:
    """Admins and supervisors: the people who can run a sitting.

    Trainees are members too, and counting them here would tell an organisation
    its team was staffed when nobody could supervise anything.
    """
    roles = sorted(domain.ORG_ADMIN_ROLES | {domain.ASSIGNED_STAFF_ROLE})
    return await repository.count_memberships(session, org_id, roles=roles)
