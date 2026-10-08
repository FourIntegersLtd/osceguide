"""Recording what the platform did.

The audit log is `tenancy`'s table, and every slice that lets a platform admin change
something — an entitlement, an attempt, a payment — calls this rather than writing the
table directly. A platform act has no organisation: `org_id` is left empty, which is what
`GET /platform/audit` reads back and the per-organisation log does not.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.tenancy import repository


async def record(
    session: AsyncSession,
    *,
    actor: Principal,
    action: str,
    target_type: str,
    target_id: str,
    summary: str | None = None,
    meta: dict[str, Any] | None = None,
    at: datetime | None = None,
) -> None:
    """One audit row for one platform act, in the caller's transaction.

    Written with the change it describes, so a rollback takes both: an audit
    row for something that did not happen is worse than none.
    """
    await repository.write_audit(
        session,
        org_id=None,
        actor_user_id=actor.user_id,
        actor_email=actor.email,
        action=action,
        at=at,
        target_type=target_type,
        target_id=target_id,
        summary=summary,
        meta=meta,
    )


async def record_for_org(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    actor: Principal | None,
    action: str,
    target_type: str,
    target_id: str,
    summary: str | None = None,
    meta: dict[str, Any] | None = None,
    at: datetime | None = None,
) -> None:
    """`record`'s twin for an institution's own act on its own data — an
    organisation admin anonymising a trainee, say — read back by
    `GET /orgs/{org_slug}/audit` rather than the platform's own log. `actor=None` is a
    directory connector (SCIM), which is no person."""
    await repository.write_audit(
        session,
        org_id=org_id,
        actor_user_id=actor.user_id if actor else None,
        actor_email=actor.email if actor else None,
        action=action,
        at=at,
        target_type=target_type,
        target_id=target_id,
        summary=summary,
        meta=meta,
    )
