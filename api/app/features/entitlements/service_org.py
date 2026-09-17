"""An institution granting and withdrawing access.

Split from `service.py`, which is the gate every attempt passes through; this
is the other side of it, the grant an organisation makes. The README promised
`POST /orgs/{slug}/entitlements` from the start and only `billing` ever
called `grant`, so an institution's students had the consumer free trial and
then a paywall.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.catalog import service as catalog
from app.features.catalog.errors import UnknownExamError as CatalogUnknownExam
from app.features.entitlements import errors, repository, service
from app.features.entitlements.schemas import EntitlementRead
from app.features.identity import service as identity


async def grant_for_org(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    email: str,
    exam_code: str,
    ends_at: datetime | None,
    actor: Principal,
) -> EntitlementRead:
    """Grant one person access to an exam, on the institution's account.

    The person must already have an account — rostering or a membership
    invites them, so by the time an administrator grants access they do.
    """
    user = await identity.user_ref_by_email(session, email)
    if user is None:
        raise errors.GranteeNotFound()
    try:
        return await service.grant(
            session,
            user_id=user.id,
            exam_code=exam_code,
            source="org_grant",
            source_ref=str(org_id),
            org_id=org_id,
            ends_at=ends_at,
            granted_by=actor.user_id,
        )
    except CatalogUnknownExam as exc:
        raise errors.UnknownExamError(str(exc)) from exc


async def list_for_org(session: AsyncSession, org_id: uuid.UUID, *, now: datetime) -> list[EntitlementRead]:
    out = []
    for row in await repository.for_org(session, org_id):
        code = await catalog.exam_code_by_id(session, row.exam_id)
        out.append(service._read(row, code or "", now=now))
    return out


async def revoke_for_org(
    session: AsyncSession, org_id: uuid.UUID, entitlement_id: uuid.UUID, *, now: datetime
) -> EntitlementRead:
    """Withdraw a grant. The row stays, with `revoked_at`, so the history holds."""
    row = await repository.by_id_for_org(session, org_id, entitlement_id)
    if row is None:
        raise errors.EntitlementNotFound()
    if row.revoked_at is None:
        await repository.revoke(session, entitlement_id, at=now)
        await session.refresh(row)
    code = await catalog.exam_code_by_id(session, row.exam_id)
    return service._read(row, code or "", now=now)
