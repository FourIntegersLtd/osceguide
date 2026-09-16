"""Tenancy use cases and the membership lookup `identity` depends on."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership as TokenMembership
from app.features.tenancy import repository


async def memberships_for_token(session: AsyncSession, user_id: uuid.UUID) -> list[TokenMembership]:
    """The claims form of a user's memberships.

    Returns the token's shape, not the table's: a mapped row would drag lazy
    relationships into a JWT, and the claims deliberately carry only what
    authorisation needs — org, slug, role, surface.
    """
    rows = await repository.memberships_for_user(session, user_id)
    out: list[TokenMembership] = []
    for row in rows:
        org = await repository.organization_by_id(session, row.org_id)
        if org is None:
            continue
        out.append(
            TokenMembership(org_id=org.id, org_slug=org.slug, role=row.role, surface=row.product_surface)
        )
    return out
