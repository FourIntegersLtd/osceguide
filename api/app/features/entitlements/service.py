"""The one place that answers whether an attempt may start."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import service as catalog
from app.features.catalog.service import resolve_exam
from app.features.entitlements import domain, repository
from app.features.entitlements.errors import NotEntitled
from app.features.entitlements.models import Entitlement
from app.features.entitlements.schemas import EntitlementRead

# Re-exported so a caller above this slice can build one without reaching into
# its domain module: `attempts` counts the attempts, this slice owns the rule.
TrialState = domain.TrialState


def _to_grant(row: Entitlement) -> domain.Grant:
    return domain.Grant(
        source=row.source, starts_at=row.starts_at, ends_at=row.ends_at, revoked_at=row.revoked_at
    )


async def decide(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    exam_id: uuid.UUID,
    now: datetime,
    trial: domain.TrialState | None = None,
) -> domain.Decision:
    rows = await repository.for_user_and_exam(session, user_id, exam_id)
    return domain.decide([_to_grant(r) for r in rows], now=now, trial=trial)


async def require(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    exam_id: uuid.UUID,
    now: datetime,
    trial: domain.TrialState | None = None,
) -> domain.Decision:
    """Assert access, or refuse the request. Every attempt-creating path calls this."""
    decision = await decide(session, user_id=user_id, exam_id=exam_id, now=now, trial=trial)
    if not decision.allowed:
        raise NotEntitled(details={"reason": decision.reason})
    return decision


async def grant(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    exam_code: str,
    source: str,
    source_ref: str | None = None,
    org_id: uuid.UUID | None = None,
    ends_at: datetime | None = None,
    granted_by: uuid.UUID | None = None,
) -> EntitlementRead:
    exam = await resolve_exam(session, exam_code, org_id=org_id)
    row = await repository.grant(
        session,
        user_id=user_id,
        exam_id=exam.id,
        source=source,
        source_ref=source_ref,
        org_id=org_id,
        ends_at=ends_at,
        granted_by=granted_by,
    )
    return _read(row, exam.code, now=row.starts_at)


async def list_for_user(session: AsyncSession, user_id: uuid.UUID, *, now: datetime) -> list[EntitlementRead]:
    out = []
    for row in await repository.for_user(session, user_id):
        code = await catalog.exam_code_by_id(session, row.exam_id)
        out.append(_read(row, code or "", now=now))
    return out


def _read(row: Entitlement, exam_code: str, *, now: datetime) -> EntitlementRead:
    return EntitlementRead(
        id=row.id,
        user_id=row.user_id,
        exam_id=row.exam_id,
        exam_code=exam_code,
        source=row.source,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        revoked_at=row.revoked_at,
        live=_to_grant(row).live_at(now),
    )
