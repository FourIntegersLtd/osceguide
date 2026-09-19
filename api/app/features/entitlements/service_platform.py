"""Entitlements as the people who answer support see them, and what they may do.

"I paid and I cannot practise" is answered from here: every grant a person
has ever held, live or not, with its source and who made it. And when the
answer is "nothing granted it", the grant itself — source `admin`, which the
table has always allowed and no route ever wrote.

Every write leaves an audit row with no organisation: a platform act, kept in
the same log as the org's own so one read tells the whole story.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.catalog import service as catalog
from app.features.catalog.errors import UnknownExamError as CatalogUnknownExam
from app.features.entitlements import domain, errors, repository, service
from app.features.entitlements.models import Entitlement
from app.features.entitlements.schemas import PlatformEntitlementRead
from app.features.identity import service as identity
from app.features.tenancy import service_audit


async def _require_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    if await identity.user_ref_by_id(session, user_id) is None:
        raise errors.GranteeNotFound()


async def _require(session: AsyncSession, entitlement_id: uuid.UUID) -> Entitlement:
    row = await repository.by_id(session, entitlement_id)
    if row is None:
        raise errors.EntitlementNotFound("No such entitlement")
    return row


async def list_for_user(
    session: AsyncSession, user_id: uuid.UUID, *, now: datetime
) -> list[PlatformEntitlementRead]:
    """Every grant this person has held, newest last, revoked ones included."""
    await _require_user(session, user_id)
    return [await _read(session, row, now=now) for row in await repository.for_user(session, user_id)]


async def grant(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    exam_code: str,
    ends_at: datetime | None,
    note: str,
    actor: Principal,
    now: datetime,
) -> PlatformEntitlementRead:
    """Grant access on the platform's own account.

    Idempotent on what was asked: a live `admin` grant for the same exam with
    the same end already answers the request, so a double-click cannot leave
    two rows saying the same thing.
    """
    await _require_user(session, user_id)
    try:
        exam = await catalog.resolve_exam(session, exam_code, org_id=None)
    except CatalogUnknownExam as exc:
        raise errors.UnknownExamError(str(exc)) from exc
    for row in await repository.for_user_and_exam(session, user_id, exam.id):
        if row.source == "admin" and row.ends_at == ends_at and service._to_grant(row).live_at(now):
            return await _read(session, row, now=now)
    created = await service.grant(
        session,
        user_id=user_id,
        exam_code=exam_code,
        source="admin",
        source_ref=f"admin:{actor.user_id}",
        ends_at=ends_at,
        granted_by=actor.user_id,
    )
    await service_audit.record(
        session,
        actor=actor,
        action="entitlement.granted",
        target_type="entitlement",
        target_id=str(created.id),
        summary=f"{exam_code} for user {user_id}: {note}",
        meta={"user_id": str(user_id), "exam_code": exam_code, "ends_at": _iso(ends_at), "note": note},
    )
    return await _read(session, await _require(session, created.id), now=now)


async def extend(
    session: AsyncSession,
    entitlement_id: uuid.UUID,
    *,
    ends_at: datetime | None,
    note: str | None,
    actor: Principal,
    now: datetime,
) -> PlatformEntitlementRead:
    """Move a grant's end. A renewal is this, not a second row."""
    row = await _require(session, entitlement_id)
    if row.ends_at != ends_at:
        previous = row.ends_at
        await repository.set_ends_at(session, entitlement_id, ends_at=ends_at)
        await service_audit.record(
            session,
            actor=actor,
            action="entitlement.extended",
            target_type="entitlement",
            target_id=str(entitlement_id),
            summary=f"{_iso(previous)} -> {_iso(ends_at)}" + (f": {note}" if note else ""),
            meta={"user_id": str(row.user_id), "from": _iso(previous), "to": _iso(ends_at), "note": note},
        )
    return await _read(session, await _require(session, entitlement_id), now=now)


async def revoke(
    session: AsyncSession, entitlement_id: uuid.UUID, *, reason: str, actor: Principal, now: datetime
) -> PlatformEntitlementRead:
    """Withdraw a grant. The row stays, with `revoked_at`; twice is once."""
    row = await _require(session, entitlement_id)
    if row.revoked_at is None:
        await repository.revoke(session, entitlement_id, at=now)
        await service_audit.record(
            session,
            actor=actor,
            action="entitlement.revoked",
            target_type="entitlement",
            target_id=str(entitlement_id),
            summary=reason,
            meta={"user_id": str(row.user_id), "reason": reason},
        )
    return await _read(session, await _require(session, entitlement_id), now=now)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


async def _read(session: AsyncSession, row: Entitlement, *, now: datetime) -> PlatformEntitlementRead:
    code = await catalog.exam_code_by_id(session, row.exam_id)
    base = service._read(row, code or "", now=now)
    return PlatformEntitlementRead(
        **base.model_dump(), source_ref=row.source_ref, org_id=row.org_id, granted_by=row.granted_by
    )


_ = domain  # the live rule is `Grant.live_at`, reached through `service._to_grant`
