"""An institution granting and withdrawing access.

`service.py` is the gate every attempt passes through; this is the other side of it, the grant
an organisation makes.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.catalog import service as catalog
from app.features.catalog.errors import UnknownExamError as CatalogUnknownExam
from app.features.entitlements import errors, repository, service
from app.features.entitlements.schemas import EntitlementRead
from app.features.identity import service as identity
from app.features.tenancy import service_audit as tenancy_audit


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
        granted = await service.grant(
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
    await tenancy_audit.record_for_owner(
        session,
        org_id=org_id,
        actor=actor,
        action="entitlement.granted",
        target_type="entitlement",
        target_id=str(granted.id),
        summary=f"Granted {exam_code} to {email}",
    )
    return granted


async def list_for_org(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    now: datetime,
    limit: int,
    cursor: dict[str, Any] | None,
    search: str | None = None,
) -> tuple[list[EntitlementRead], str | None]:
    """A page of what this institution has granted, revoked ones included.

    `search`, if given, narrows to a grant whose grantee's name or email, or
    whose exam code, contains it — resolved through `identity` and `catalog`,
    which own those tables, rather than joining them here.
    """
    term = (search or "").strip()
    matching_user_ids: list[uuid.UUID] = []
    matching_exam_ids: list[uuid.UUID] = []
    if term:
        matching_user_ids = await identity.user_ids_matching(session, term)
        matching_exam_ids = await catalog.exam_ids_matching_code(session, term)
    entitlements, next_cursor = await repository.for_org(
        session,
        org_id,
        limit=limit,
        cursor=cursor,
        matching_user_ids=matching_user_ids,
        matching_exam_ids=matching_exam_ids,
        has_search=bool(term),
    )
    reads = []
    for entitlement in entitlements:
        code = await catalog.exam_code_by_id(session, entitlement.exam_id)
        reads.append(service._read(entitlement, code or "", now=now))
    return reads, next_cursor


async def revoke_for_org(
    session: AsyncSession, org_id: uuid.UUID, entitlement_id: uuid.UUID, *, actor: Principal, now: datetime
) -> EntitlementRead:
    """Withdraw a grant. The row stays, with `revoked_at`, so the history holds."""
    entitlement = await repository.by_id_for_org(session, org_id, entitlement_id)
    if entitlement is None:
        raise errors.EntitlementNotFound()
    if entitlement.revoked_at is None:
        await repository.revoke(session, entitlement_id, at=now)
        await session.refresh(entitlement)
        await tenancy_audit.record_for_owner(
            session,
            org_id=org_id,
            actor=actor,
            action="entitlement.revoked",
            target_type="entitlement",
            target_id=str(entitlement_id),
            summary="Access grant withdrawn",
        )
    code = await catalog.exam_code_by_id(session, entitlement.exam_id)
    return service._read(entitlement, code or "", now=now)
