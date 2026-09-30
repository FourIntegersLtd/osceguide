"""Bulk actions on a team: seating a whole team in one request, or revoking
or re-inviting a selection of existing memberships.

One duplicate in a list of forty must not refuse the other thirty-nine, and the
administrator has to be told which rows were skipped and why. Each row still goes through
the matching single-row function in `service_memberships` — `add_membership`,
`set_membership_revoked`, `resend_invitation` — so a bulk action is exactly the same act
as a single one, clicked many times, and cannot drift from it or skip its audit trail.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.tenancy import repository, service_memberships
from app.features.tenancy.errors import InvitationNotPending, MembershipExists, MembershipNotFound
from app.features.tenancy.schemas import (
    BulkMembershipInvitationResult,
    BulkMembershipRevokeResult,
    BulkMembershipsResult,
    CreateMembership,
    SkippedMembership,
)


async def add_memberships(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    entries: list[CreateMembership],
    actor: Principal,
    now: datetime,
) -> BulkMembershipsResult:
    """Seat every person who can be seated; report the rest.

    Duplicates within the upload are caught before the second one is written,
    so a sheet that lists the same tutor twice invites them once and says so
    rather than failing on the second row.
    """
    outcome = BulkMembershipsResult()
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        key = (entry.email.strip().lower(), entry.role.strip().lower())
        if key in seen:
            outcome.skipped.append(
                SkippedMembership(email=entry.email, role=entry.role, code=MembershipExists.code)
            )
            continue
        seen.add(key)
        try:
            created = await service_memberships.add_membership(
                session,
                org_id,
                email=entry.email,
                role=entry.role,
                product_surface=entry.product_surface,
                actor=actor,
                now=now,
            )
        except MembershipExists as exc:
            outcome.skipped.append(SkippedMembership(email=entry.email, role=entry.role, code=exc.code))
            continue
        outcome.created.append(created)
    return outcome


def _dedupe_ids(membership_ids: Sequence[uuid.UUID]) -> list[uuid.UUID]:
    """Keep the first occurrence of each id, in the order the caller sent them.

    A screen posting a selection can repeat an id (a double click, a stale
    checkbox); the result carries one row per id, not one per repetition.
    """
    return list(dict.fromkeys(membership_ids))


async def revoke_memberships(
    session: AsyncSession,
    org_id: uuid.UUID,
    membership_ids: Sequence[uuid.UUID],
    *,
    actor: Principal,
    now: datetime,
) -> list[BulkMembershipRevokeResult]:
    """Revoke a selection of memberships, one `service_memberships.set_membership_revoked`
    call per row.

    The row's state is read first only to tell the caller "revoked" from
    "already_revoked" apart — `set_membership_revoked` itself has no third state and
    would happily re-stamp an already-revoked row with a fresh timestamp and a second
    audit entry, so an already-revoked id is left untouched rather than re-written.

    Neither a "last admin" nor a "self-revoke" refusal exists on the single-row route
    today, so this batch does not invent one either: see the PR notes for that gap.
    """
    results: list[BulkMembershipRevokeResult] = []
    for membership_id in _dedupe_ids(membership_ids):
        membership = await repository.membership_by_id(session, org_id, membership_id)
        if membership is None:
            results.append(BulkMembershipRevokeResult(membership_id=membership_id, outcome="not_found"))
            continue
        if membership.revoked_at is not None:
            results.append(BulkMembershipRevokeResult(membership_id=membership_id, outcome="already_revoked"))
            continue
        await service_memberships.set_membership_revoked(
            session, org_id, membership_id, revoked=True, actor=actor, now=now
        )
        results.append(BulkMembershipRevokeResult(membership_id=membership_id, outcome="revoked"))
    return results


async def resend_membership_invitations(
    session: AsyncSession, org_id: uuid.UUID, membership_ids: Sequence[uuid.UUID], *, now: datetime
) -> list[BulkMembershipInvitationResult]:
    """Resend the choose-a-password link to a selection of memberships, one
    `service_memberships.resend_invitation` call per row.

    The single-row route only ever refuses with `invitation_not_pending` (the person
    already has a password, or the account is otherwise not waiting on one) — there is
    no rule today that refuses a revoked membership, so this batch does not invent a
    `"revoked"` outcome for one; see the PR notes for that gap.
    """
    results: list[BulkMembershipInvitationResult] = []
    for membership_id in _dedupe_ids(membership_ids):
        try:
            await service_memberships.resend_invitation(session, org_id, membership_id, now=now)
        except MembershipNotFound:
            results.append(BulkMembershipInvitationResult(membership_id=membership_id, outcome="not_found"))
            continue
        except InvitationNotPending:
            results.append(
                BulkMembershipInvitationResult(membership_id=membership_id, outcome="already_accepted")
            )
            continue
        results.append(BulkMembershipInvitationResult(membership_id=membership_id, outcome="sent"))
    return results
