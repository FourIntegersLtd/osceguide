"""The audit log, read across every organisation.

Split from `service_platform.py` at the file cap. The platform's own rows —
who granted the console to whom, who deactivated an account — were written
from the start with no organisation and, until this read existed, nothing
could read them back.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.tenancy import repository, repository_platform
from app.features.tenancy.errors import OrgNotFound
from app.features.tenancy.models import AuditEntry
from app.features.tenancy.schemas import PlatformAuditRead


async def list_audit(
    session: AsyncSession,
    *,
    org_slug: str | None,
    actor_email: str | None,
    action: str | None,
    limit: int,
    cursor: dict[str, Any] | None,
) -> tuple[list[PlatformAuditRead], str | None]:
    """The audit log across every organisation, and the platform's own rows.

    Those rows — who granted the console to whom, who deactivated an account —
    were written from the start with no organisation and, until this read
    existed, nothing could read them back.
    """
    org_id: uuid.UUID | None = None
    if org_slug:
        org = await repository.organization_by_slug(session, org_slug)
        if org is None:
            raise OrgNotFound()
        org_id = org.id
    rows, next_cursor = await repository_platform.list_audit_across_orgs(
        session, org_id=org_id, actor_email=actor_email, action=action, limit=limit, cursor=cursor
    )
    return [platform_audit_read(row) for row in rows], next_cursor


def platform_audit_read(row: AuditEntry) -> PlatformAuditRead:
    return PlatformAuditRead(
        id=row.id,
        actor_email=row.actor_email,
        action=row.action,
        target_type=row.target_type,
        target_id=row.target_id,
        summary=row.summary,
        at=row.at,
        org_id=row.org_id,
        actor_user_id=row.actor_user_id,
        meta=row.meta,
    )
