"""Who is in an organisation, and with what role."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.errors import Forbidden, InvalidInput
from app.features.identity import service as identity
from app.features.identity import service_invitations as invitations
from app.features.roster.schemas import InvitationRead
from app.features.tenancy import domain, repository
from app.features.tenancy.errors import (
    InvitationNotPending,
    MembershipExists,
    MembershipNotFound,
    OrgNotFound,
)
from app.features.tenancy.schemas import MembershipRead


def _guard_role_grant(actor: Principal, org_id: uuid.UUID, role: str) -> None:
    """Refuse a role the granter is not entitled to write.

    `OrgAdmin` admits `partner_admin`, which must never examine, and `role` is a free string:
    without this a partner admin could seat itself or anyone as `institution_admin` or
    `owner`. An unknown role is a bad request; a known role above the granter's tier is
    forbidden. A platform admin may write any known role.
    """
    if not domain.is_known_role(role):
        raise InvalidInput(f"Unknown role: {role!r}")
    if actor.is_platform_admin:
        return
    membership = next((membership for membership in actor.memberships if membership.org_id == org_id), None)
    actor_role = membership.role if membership else None
    if not domain.may_grant_role(actor_role, role):
        raise Forbidden("You cannot grant a role above your own.")


async def list_memberships(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None,
    search: str | None = None,
    status: str | None = None,
) -> tuple[list[MembershipRead], str | None]:
    """A page of an organisation's memberships, with each person's email attached.

    `status`, if given, keeps only `active` or only `revoked` memberships.

    `search`, if given, narrows to a membership whose role or person matches
    it: role by substring, person by email or name (resolved through
    `identity`, which owns that table), or by their id typed in exactly.
    """
    term = (search or "").strip()
    matching_user_ids: list[uuid.UUID] = []
    exact_user_id: uuid.UUID | None = None
    if term:
        matching_user_ids = await identity.user_ids_matching(session, term)
        try:
            exact_user_id = uuid.UUID(term)
        except ValueError:
            exact_user_id = None
    memberships, next_cursor = await repository.list_memberships(
        session,
        org_id,
        limit=limit,
        cursor=cursor,
        role_pattern=f"%{term}%" if term else None,
        matching_user_ids=matching_user_ids,
        exact_user_id=exact_user_id,
        status=status,
    )
    # The addresses are read for the page instead of being left null. A team
    # list without an email can only show the front of a user id, which is a
    # uuid printed as if it were a name; the one join is the whole of the fix.
    people = await identity.user_refs_by_ids(session, [membership.user_id for membership in memberships])
    return [
        _membership_read(
            membership, email=people[membership.user_id].email if membership.user_id in people else None
        )
        for membership in memberships
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
    """Put somebody in an organisation, by email.

    An address with no account is invited rather than refused: the account is created
    without a password and the person is emailed a link to choose one.
    """
    _guard_role_grant(actor, org_id, role)
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
    """Change what role a membership holds, refusing a role the actor may not grant."""
    _guard_role_grant(actor, org_id, role)
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


async def _read_with_email(session: AsyncSession, membership: Any) -> MembershipRead:
    """A membership answered the way the list answers it, with the email attached.

    `add_membership` does not need this — it looked the person up by address already.
    """
    people = await identity.user_refs_by_ids(session, [membership.user_id])
    return _membership_read(
        membership, email=people[membership.user_id].email if membership.user_id in people else None
    )


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


async def resend_invitation(
    session: AsyncSession, org_id: uuid.UUID, membership_id: uuid.UUID, *, now: datetime
) -> InvitationRead:
    """Send the choose-a-password link to this staff member again.

    A staff membership is always attached to an account (unlike a roster row),
    so this only needs `identity.reissue_invitation`. Returns 409
    `invitation_not_pending` if the person already has a password or signs in
    through SSO.
    """
    membership = await _require_membership(session, org_id, membership_id)
    org = await repository.organization_by_id(session, org_id)
    invited_to = org.name if org else "your organisation"
    people = await identity.user_refs_by_ids(session, [membership.user_id])
    ref = people.get(membership.user_id)
    if ref is None:
        raise MembershipNotFound()
    if not await invitations.reissue_invitation(
        session, user_id=membership.user_id, invited_to=invited_to, now=now
    ):
        raise InvitationNotPending()
    return InvitationRead(email=ref.email, invited_to=invited_to)


async def _require_membership(session: AsyncSession, org_id: uuid.UUID, membership_id: uuid.UUID) -> Any:
    """Fetch a membership, or refuse if this organisation has none by that id."""
    membership = await repository.membership_by_id(session, org_id, membership_id)
    if membership is None:
        raise MembershipNotFound()
    return membership


def _membership_read(membership: Any, *, email: str | None = None, invited: bool = False) -> MembershipRead:
    """Shape a membership row into what a route may return."""
    return MembershipRead(
        id=membership.id,
        user_id=membership.user_id,
        email=email,
        role=membership.role,
        product_surface=membership.product_surface,
        status=membership.status,
        revoked_at=membership.revoked_at,
        invited=invited,
    )


async def count_staff(session: AsyncSession, org_id: uuid.UUID) -> int:
    """Admins and supervisors: the people who can run a sitting.

    Trainees are members too, and counting them here would tell an organisation
    its team was staffed when nobody could supervise anything.
    """
    roles = sorted(domain.ORG_ADMIN_ROLES | {domain.ASSIGNED_STAFF_ROLE})
    return await repository.count_memberships(session, org_id, roles=roles)
