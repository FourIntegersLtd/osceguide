"""The one place that answers whether an attempt may start."""

from __future__ import annotations

import uuid
from collections.abc import Collection
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


def _to_grant(entitlement: Entitlement) -> domain.Grant:
    """Turn a stored row into the plain-data shape `domain.decide` reasons
    about."""
    return domain.Grant(
        source=entitlement.source,
        starts_at=entitlement.starts_at,
        ends_at=entitlement.ends_at,
        revoked_at=entitlement.revoked_at,
    )


async def decide(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    exam_id: uuid.UUID,
    now: datetime,
    trial: domain.TrialState | None = None,
) -> domain.Decision:
    """The allowed/refused verdict for one exam, without raising anything.

    `require` is what a route calls; this is for a caller that wants to
    handle a "no" itself rather than catch `NotEntitled`.
    """
    entitlements = await repository.for_user_and_exam(session, user_id, exam_id)
    return domain.decide([_to_grant(entitlement) for entitlement in entitlements], now=now, trial=trial)


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
    """Record a new grant, resolving the exam code through the catalogue
    first so a code nobody has published fails here rather than leaving a
    dangling foreign key."""
    exam = await resolve_exam(session, exam_code, org_id=org_id)
    entitlement = await repository.grant(
        session,
        user_id=user_id,
        exam_id=exam.id,
        source=source,
        source_ref=source_ref,
        org_id=org_id,
        ends_at=ends_at,
        granted_by=granted_by,
    )
    return _read(entitlement, exam.code, now=entitlement.starts_at)


async def revoked_ids(session: AsyncSession, entitlement_ids: Collection[uuid.UUID]) -> set[uuid.UUID]:
    """Which of these grants have been withdrawn."""
    return await repository.revoked_ids(session, entitlement_ids)


async def withdraw(session: AsyncSession, entitlement_id: uuid.UUID, *, now: datetime) -> None:
    """Take a grant back because the money for it went back (refund, dispute). No staff actor:
    the processor did it. Twice is once."""
    await repository.revoke(session, entitlement_id, at=now)


async def list_for_user(session: AsyncSession, user_id: uuid.UUID, *, now: datetime) -> list[EntitlementRead]:
    """Every grant this account has ever held, revoked and lapsed ones
    included, each with `live` computed against `now`.

    This is history, not access: a caller deciding what to show or allow
    must filter on `live` itself rather than assume every row here is current.
    """
    reads = []
    for entitlement in await repository.for_user(session, user_id):
        code = await catalog.exam_code_by_id(session, entitlement.exam_id)
        reads.append(_read(entitlement, code or "", now=now))
    return reads


def _read(entitlement: Entitlement, exam_code: str, *, now: datetime) -> EntitlementRead:
    """Build the response shape for one row, with `live` computed against
    `now` rather than stored."""
    return EntitlementRead(
        id=entitlement.id,
        user_id=entitlement.user_id,
        exam_id=entitlement.exam_id,
        exam_code=exam_code,
        source=entitlement.source,
        starts_at=entitlement.starts_at,
        ends_at=entitlement.ends_at,
        revoked_at=entitlement.revoked_at,
        live=_to_grant(entitlement).live_at(now),
    )
