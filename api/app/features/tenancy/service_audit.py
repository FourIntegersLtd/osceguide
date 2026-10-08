"""Recording what the platform did.

The audit log is `tenancy`'s table, and every slice that lets a platform admin change
something — an entitlement, an attempt, a payment — calls this rather than writing the
table directly. A platform act has no organisation: `org_id` is left empty, which is what
`GET /platform/audit` reads back and the per-organisation log does not.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, overload

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.tenancy import repository


@dataclass(frozen=True)
class Connector:
    """An act by a directory connector (SCIM): a token, no person, so no actor email."""


SCIM_CONNECTOR = Connector()


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


async def _record_for_org(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    actor: Principal | Connector,
    action: str,
    target_type: str,
    target_id: str,
    summary: str | None = None,
    meta: dict[str, Any] | None = None,
    at: datetime | None = None,
) -> None:
    """`record`'s twin for an institution's own act on its own data — an
    organisation admin anonymising a trainee, say — read back by
    `GET /orgs/{org_slug}/audit` rather than the platform's own log. A `Connector` actor
    is a directory connector (SCIM), which is no person."""
    await repository.write_audit(
        session,
        org_id=org_id,
        actor_user_id=actor.user_id if isinstance(actor, Principal) else None,
        actor_email=actor.email if isinstance(actor, Principal) else None,
        action=action,
        at=at,
        target_type=target_type,
        target_id=target_id,
        summary=summary,
        meta=meta,
    )


@overload
async def record_for_owner(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    actor: Principal | Connector,
    action: str,
    target_type: str,
    target_id: str,
    summary: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """Record one act inside an organisation's own audit log."""


@overload
async def record_for_owner(
    session: AsyncSession,
    *,
    org_id: None,
    actor: Principal,
    action: str,
    target_type: str,
    target_id: str,
    summary: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """Record one platform-admin act in the platform's audit log."""


async def record_for_owner(
    session: AsyncSession,
    *,
    org_id: uuid.UUID | None,
    actor: Principal | Connector,
    action: str,
    target_type: str,
    target_id: str,
    summary: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """One audit row in its owner's log: the organisation's own, or the platform's when `org_id`
    is empty (the library and the platform catalogue). A connector acts only inside an
    organisation, which the overloads enforce."""
    if org_id is None:
        assert isinstance(actor, Principal)  # unreachable through the overloads
        await record(
            session,
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            summary=summary,
            meta=meta,
        )
    else:
        await _record_for_org(
            session,
            org_id=org_id,
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            summary=summary,
            meta=meta,
        )
