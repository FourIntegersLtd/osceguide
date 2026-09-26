"""Seating a whole team in one request.

One duplicate in a list of forty must not refuse the other thirty-nine, and the
administrator has to be told which rows were skipped and why. Each row still goes through
`add_membership`, so a bulk invite is exactly the same act as a single one and cannot
drift from it.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.tenancy import service_memberships
from app.features.tenancy.errors import MembershipExists
from app.features.tenancy.schemas import (
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
