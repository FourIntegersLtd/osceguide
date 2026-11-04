"""Storage for organisations, memberships and the audit log.

Every org-scoped method takes `org_id` first. That is not a style preference:
it is the reason a cross-tenant read has to be written deliberately rather than
reached by forgetting a filter, which is how `b2b` leaked through
`find_slot_by_id_global`.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_wording import RELAYED_PASSWORD_NOTE, roster_added_summary
from app.core.pagination import keyset_page
from app.core.search import contains_text
from app.core.tenancy import forget_org_active
from app.features.tenancy.domain import END_USER_ROLES, ORG_ADMIN_ROLES
from app.features.tenancy.models import AuditEntry, Membership, Organization


async def create_organization(
    session: AsyncSession, *, slug: str, name: str, org_type: str = "institution", status: str = "trial"
) -> Organization:
    """Provision a new organisation."""
    org = Organization(slug=slug.strip(), name=name, org_type=org_type, status=status)
    session.add(org)
    # Flushed and refreshed so the caller gets the generated id and the
    # server-side defaults (created_at, status) rather than None.
    await session.flush()
    await session.refresh(org)
    return org


async def organization_by_slug(session: AsyncSession, slug: str) -> Organization | None:
    """Find an organisation by its slug."""
    stmt = select(Organization).where(Organization.slug == slug.strip())
    return (await session.execute(stmt)).scalar_one_or_none()


async def organization_by_id(session: AsyncSession, org_id: uuid.UUID) -> Organization | None:
    return (await session.execute(select(Organization).where(Organization.id == org_id))).scalar_one_or_none()


async def set_organization_status(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    status: str,
    suspended_at: datetime | None = None,
    suspended_by: uuid.UUID | None = None,
) -> None:
    """Change an organisation's status, e.g. suspending or restoring it.

    Every route to a changed status passes through here (suspend, restore, a lapsed contract), so
    it is where the cached "this organisation is active" answer is dropped once the change commits.
    """
    slug = (
        await session.execute(
            update(Organization)
            .where(Organization.id == org_id)
            .values(status=status, suspended_at=suspended_at, suspended_by=suspended_by)
            .returning(Organization.slug)
        )
    ).scalar_one_or_none()
    if slug is not None:
        forget_org_active(session, slug)


# --- memberships -----------------------------------------------------------


async def add_membership(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
    product_surface: str | None = None,
) -> Membership:
    """Grant a person a role at an organisation."""
    membership = Membership(org_id=org_id, user_id=user_id, role=role, product_surface=product_surface)
    session.add(membership)
    # Flushed so the caller gets the id and the server-side status: returned
    # unflushed, the row read back as `id=None` and the route serialising it
    # failed after the insert had already been written.
    await session.flush()
    await session.refresh(membership)
    return membership


async def staff_mfa_flags(session: AsyncSession, user_id: uuid.UUID) -> list[tuple[str, bool]]:
    """Each live membership's role, and whether that organisation requires staff MFA."""
    stmt = (
        select(Membership.role, Organization.require_staff_mfa)
        .join(Organization, Organization.id == Membership.org_id)
        .where(Membership.user_id == user_id, Membership.revoked_at.is_(None))
    )
    return [(role, required) for role, required in (await session.execute(stmt)).all()]


async def memberships_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[Membership]:
    """Not org-scoped by design: this answers "which orgs is this person in?",
    which is what login needs before any workspace exists."""
    stmt = (
        select(Membership)
        .where(Membership.user_id == user_id, Membership.revoked_at.is_(None))
        .order_by(Membership.created_at)
    )
    return list((await session.execute(stmt)).scalars())


async def organizations_by_ids(session: AsyncSession, org_ids: set[uuid.UUID]) -> list[Organization]:
    """Several organisations in one query."""
    if not org_ids:
        return []
    return list((await session.execute(select(Organization).where(Organization.id.in_(org_ids)))).scalars())


async def live_memberships_with_orgs(
    session: AsyncSession, user_id: uuid.UUID
) -> list[tuple[Membership, Organization]]:
    """A person's memberships and the organisations they are in, in one query.

    Was a query per membership, on every login and every refresh. The join also
    drops memberships whose organisation has gone, which the two-step version
    silently kept as a `None` org.
    """
    stmt = (
        select(Membership, Organization)
        .join(Organization, Organization.id == Membership.org_id)
        .where(
            Membership.user_id == user_id,
            Membership.revoked_at.is_(None),
            Membership.status != "revoked",
        )
        .order_by(Membership.created_at, Membership.id)
    )
    return [(membership, organization) for membership, organization in (await session.execute(stmt)).all()]


async def membership_for_user_in_org(
    session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, *, role: str
) -> Membership | None:
    """Find this person's membership at this organisation with this specific role."""
    stmt = select(Membership).where(
        Membership.org_id == org_id, Membership.user_id == user_id, Membership.role == role
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def memberships_for_user_in_org(
    session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID
) -> list[Membership]:
    """Every membership (live or revoked) this person holds at this organisation."""
    stmt = select(Membership).where(Membership.org_id == org_id, Membership.user_id == user_id)
    return list((await session.execute(stmt)).scalars())


async def membership_by_id(
    session: AsyncSession, org_id: uuid.UUID, membership_id: uuid.UUID
) -> Membership | None:
    """Find a membership at this organisation by its id."""
    stmt = select(Membership).where(Membership.org_id == org_id, Membership.id == membership_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_memberships(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    role_search: str | None = None,
    matching_user_ids: Sequence[uuid.UUID] | None = None,
    exact_user_id: uuid.UUID | None = None,
    status: str | None = None,
    staff_only: bool = False,
) -> tuple[list[Membership], str | None]:
    """A page of an organisation's memberships, oldest first, optionally only those with `status`.

    `staff_only` leaves out the end-user roles (trainees, practice users).

    `role_search`, `matching_user_ids` and `exact_user_id` are the three ways
    a search term can match a row — its role by `ILIKE`, its person's email or
    name (resolved to ids by `identity` before this call), or its person's id
    typed in exactly — combined with `OR`. The caller passes all three or none:
    a search with no id match still needs `matching_user_ids=[]`, which is not
    the same as no search at all.
    """
    stmt = select(Membership).where(Membership.org_id == org_id)
    if staff_only:
        stmt = stmt.where(Membership.role.not_in(sorted(END_USER_ROLES)))
    if status is not None:
        stmt = stmt.where(Membership.status == status)
    if role_search is not None:
        conditions: list[Any] = [contains_text(Membership.role, role_search)]
        if matching_user_ids:
            conditions.append(Membership.user_id.in_(list(matching_user_ids)))
        if exact_user_id is not None:
            conditions.append(Membership.user_id == exact_user_id)
        stmt = stmt.where(or_(*conditions))
    return await keyset_page(
        session,
        stmt,
        sort_col=Membership.created_at,
        id_col=Membership.id,
        limit=limit,
        cursor=cursor,
        descending=False,
    )


async def set_membership_role(
    session: AsyncSession, org_id: uuid.UUID, membership_id: uuid.UUID, *, role: str
) -> None:
    """Change what role a membership holds."""
    await session.execute(
        update(Membership)
        .where(Membership.org_id == org_id, Membership.id == membership_id)
        .values(role=role)
    )


async def set_membership_revoked(
    session: AsyncSession, org_id: uuid.UUID, membership_id: uuid.UUID, *, at: datetime | None
) -> None:
    """Revoke a membership (a timestamp) or restore it (`None`)."""
    await session.execute(
        update(Membership)
        .where(Membership.org_id == org_id, Membership.id == membership_id)
        .values(revoked_at=at, status="revoked" if at else "active")
    )


# --- audit -----------------------------------------------------------------


async def temporary_password_was_relayed(session: AsyncSession, *, user_id: uuid.UUID, email: str) -> bool:
    """Whether the audit log shows an admin gave this account a password by hand: a seat or
    team add, a roster add of this address, or a re-issue."""
    stmt = (
        select(AuditEntry.id)
        .where(
            or_(
                (AuditEntry.action == "membership.added")
                & (AuditEntry.target_id == str(user_id))
                & AuditEntry.summary.endswith(RELAYED_PASSWORD_NOTE, autoescape=True),
                (AuditEntry.action == "user.temporary_password_reissued")
                & (AuditEntry.target_id == str(user_id)),
                (AuditEntry.action == "trainee.added")
                & (
                    func.lower(AuditEntry.summary)
                    == roster_added_summary(email, RELAYED_PASSWORD_NOTE).lower()
                ),
            )
        )
        .limit(1)
    )
    return (await session.execute(stmt)).first() is not None


async def audit_count(session: AsyncSession, *, action: str, target_id: str) -> int:
    """How many entries of this action name this target."""
    stmt = (
        select(func.count())
        .select_from(AuditEntry)
        .where(AuditEntry.action == action, AuditEntry.target_id == target_id)
    )
    return int((await session.execute(stmt)).scalar_one())


async def audited_by_actor(
    session: AsyncSession, *, action: str, target_id: str, actor_user_id: uuid.UUID
) -> bool:
    """Whether this person themselves performed this action on this target."""
    stmt = (
        select(AuditEntry.id)
        .where(
            AuditEntry.action == action,
            AuditEntry.target_id == target_id,
            AuditEntry.actor_user_id == actor_user_id,
        )
        .limit(1)
    )
    return (await session.execute(stmt)).first() is not None


async def write_audit(
    session: AsyncSession,
    *,
    org_id: uuid.UUID | None,
    actor_user_id: uuid.UUID | None,
    actor_email: str | None,
    action: str,
    at: datetime | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    summary: str | None = None,
    meta: dict[str, Any] | None = None,
) -> AuditEntry:
    """Record an entry in the audit log. `org_id=None` means a platform-level act."""
    entry = AuditEntry(
        org_id=org_id,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        action=action,
        target_type=target_type,
        target_id=target_id,
        summary=summary,
        meta=meta,
        **({"at": at} if at is not None else {}),
    )
    session.add(entry)
    return entry


async def list_audit(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    actor_email: str | None = None,
    action: str | None = None,
) -> tuple[list[AuditEntry], str | None]:
    """A page of one organisation's audit log, newest first, optionally narrowed
    to one person's acts or to an action name or its prefix."""
    stmt = select(AuditEntry).where(AuditEntry.org_id == org_id)
    if actor_email:
        # Compared, not pattern-matched: a `%` in the filter must not widen it.
        stmt = stmt.where(func.lower(AuditEntry.actor_email) == actor_email.strip().lower())
    if action:
        stmt = stmt.where(AuditEntry.action.startswith(action.strip(), autoescape=True))
    return await keyset_page(
        session, stmt, sort_col=AuditEntry.at, id_col=AuditEntry.id, limit=limit, cursor=cursor
    )


async def count_memberships(
    session: AsyncSession, org_id: uuid.UUID, *, roles: Sequence[str] | None = None
) -> int:
    """Live members, optionally of certain roles. Revoked people are not staff."""
    stmt = (
        select(func.count())
        .select_from(Membership)
        .where(Membership.org_id == org_id, Membership.revoked_at.is_(None))
    )
    if roles is not None:
        stmt = stmt.where(Membership.role.in_(list(roles)))
    return int((await session.execute(stmt)).scalar_one())


async def count_organizations(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count()).select_from(Organization))).scalar_one())


async def update_organization(session: AsyncSession, org_id: uuid.UUID, **values: Any) -> None:
    """Write organisation fields. The contract end decides whether it may act, so the cached
    "active" answer is dropped once this commits (and under the old slug if the slug itself moves)."""
    old_slug = (
        await session.scalar(select(Organization.slug).where(Organization.id == org_id))
        if "slug" in values
        else None
    )
    stmt = update(Organization).where(Organization.id == org_id).values(**values)
    new_slug = (await session.execute(stmt.returning(Organization.slug))).scalar_one_or_none()
    for slug in (old_slug, new_slug):
        if slug is not None:
            forget_org_active(session, slug)


async def live_member_user_ids(session: AsyncSession, org_id: uuid.UUID) -> list[uuid.UUID]:
    """Everyone with a live membership here, whatever the role."""
    stmt = select(Membership.user_id).where(Membership.org_id == org_id, Membership.revoked_at.is_(None))
    return list((await session.execute(stmt)).scalars().unique())


async def admin_user_ids(session: AsyncSession, org_id: uuid.UUID) -> list[uuid.UUID]:
    """Everyone with a live organisation-admin membership here."""
    stmt = select(Membership.user_id).where(
        Membership.org_id == org_id,
        Membership.revoked_at.is_(None),
        Membership.role.in_(sorted(ORG_ADMIN_ROLES)),
    )
    return list((await session.execute(stmt)).scalars().unique())


async def lock_admin_memberships(session: AsyncSession, org_id: uuid.UUID) -> None:
    """Lock the live admin memberships of an organisation until the transaction ends.

    So two closures racing for its last two administrators serialise: the second counts after the
    first has committed, instead of both seeing the other still there.
    """
    stmt = (
        select(Membership.user_id)
        .where(
            Membership.org_id == org_id,
            Membership.revoked_at.is_(None),
            Membership.role.in_(sorted(ORG_ADMIN_ROLES)),
        )
        .with_for_update()
    )
    await session.execute(stmt)


async def member_user_ids(
    session: AsyncSession, org_id: uuid.UUID, user_ids: Sequence[uuid.UUID]
) -> set[uuid.UUID]:
    """Which of these people hold a live membership here, whatever the role."""
    if not user_ids:
        return set()
    stmt = select(Membership.user_id).where(
        Membership.org_id == org_id,
        Membership.user_id.in_(list(user_ids)),
        Membership.revoked_at.is_(None),
    )
    return set((await session.execute(stmt)).scalars())
