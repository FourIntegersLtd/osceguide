"""Entitlements as the people who answer support see them, and what they may do.

"I paid and I cannot practise" is answered from here: every grant a person has ever held, live
or not, with its source and who made it — plus the grant itself, source `admin`, for when the
answer is "nothing granted it".

Every write leaves an audit row with no organisation: a platform act, kept in the same log as
the org's own so one read tells the whole story.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection
from dataclasses import dataclass
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
    """Refuse before granting or listing anything for an account that does
    not exist."""
    if await identity.user_ref_by_id(session, user_id) is None:
        raise errors.GranteeNotFound()


async def _require(session: AsyncSession, entitlement_id: uuid.UUID) -> Entitlement:
    """The entitlement, or refuse: every write path needs one of these
    before it can act on it."""
    entitlement = await repository.by_id(session, entitlement_id)
    if entitlement is None:
        raise errors.EntitlementNotFound("No such entitlement")
    return entitlement


async def list_for_user(
    session: AsyncSession, user_id: uuid.UUID, *, now: datetime
) -> list[PlatformEntitlementRead]:
    """Every grant this person has held, newest last, revoked ones included."""
    await _require_user(session, user_id)
    return [
        await _read(session, entitlement, now=now)
        for entitlement in await repository.for_user(session, user_id)
    ]


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

    Idempotent on what was asked: a live `admin` grant for the same exam with the same end
    already answers the request, so a double-click cannot leave two rows saying the same thing.
    """
    await _require_user(session, user_id)
    try:
        exam = await catalog.resolve_exam(session, exam_code, org_id=None)
    except CatalogUnknownExam as exc:
        raise errors.UnknownExamError(str(exc)) from exc
    for entitlement in await repository.for_user_and_exam(session, user_id, exam.id):
        if (
            entitlement.source == "admin"
            and entitlement.ends_at == ends_at
            and service._to_grant(entitlement).live_at(now)
        ):
            return await _read(session, entitlement, now=now)
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
    entitlement = await _require(session, entitlement_id)
    if entitlement.ends_at != ends_at:
        previous = entitlement.ends_at
        await repository.set_ends_at(session, entitlement_id, ends_at=ends_at)
        await service_audit.record(
            session,
            actor=actor,
            action="entitlement.extended",
            target_type="entitlement",
            target_id=str(entitlement_id),
            summary=f"{_iso(previous)} -> {_iso(ends_at)}" + (f": {note}" if note else ""),
            meta={
                "user_id": str(entitlement.user_id),
                "from": _iso(previous),
                "to": _iso(ends_at),
                "note": note,
            },
        )
    return await _read(session, await _require(session, entitlement_id), now=now)


async def revoke(
    session: AsyncSession, entitlement_id: uuid.UUID, *, reason: str, actor: Principal, now: datetime
) -> PlatformEntitlementRead:
    """Withdraw a grant. The row stays, with `revoked_at`; twice is once."""
    entitlement = await _require(session, entitlement_id)
    if entitlement.revoked_at is None:
        await repository.revoke(session, entitlement_id, at=now)
        await service_audit.record(
            session,
            actor=actor,
            action="entitlement.revoked",
            target_type="entitlement",
            target_id=str(entitlement_id),
            summary=reason,
            meta={"user_id": str(entitlement.user_id), "reason": reason},
        )
    return await _read(session, await _require(session, entitlement_id), now=now)


def _iso(moment: datetime | None) -> str | None:
    """An audit-log-friendly rendering of a possibly-absent instant."""
    return moment.isoformat() if moment else None


async def _read(session: AsyncSession, entitlement: Entitlement, *, now: datetime) -> PlatformEntitlementRead:
    """Build the support-console response shape, adding the source and
    admin fields `service._read`'s ordinary shape leaves out."""
    code = await catalog.exam_code_by_id(session, entitlement.exam_id)
    base = service._read(entitlement, code or "", now=now)
    return PlatformEntitlementRead(
        **base.model_dump(),
        source_ref=entitlement.source_ref,
        org_id=entitlement.org_id,
        granted_by=entitlement.granted_by,
    )


_ = domain  # the live rule is `Grant.live_at`, reached through `service._to_grant`


# --- What the account directory knows about access, for many people at once.


@dataclass(frozen=True)
class LiveGrant:
    """One live grant, shaped for the account directory rather than for a
    support screen: an exam code and a source, nothing about how it was made."""

    exam_code: str
    source: str
    ends_at: datetime | None


async def live_user_ids_for_exam(session: AsyncSession, exam_code: str, *, now: datetime) -> set[uuid.UUID]:
    """Everyone entitled to this exam right now. An unknown code is nobody."""
    exam = next((ref for ref in await catalog.exam_refs(session) if ref.code == exam_code), None)
    if exam is None:
        return set()
    return await repository.live_user_ids_for_exam(session, exam.id, now=now)


async def live_grants_by_user(
    session: AsyncSession, user_ids: Collection[uuid.UUID], *, now: datetime
) -> dict[uuid.UUID, list[LiveGrant]]:
    """Every live grant among these users, grouped by user id, for a
    directory listing many people at once rather than gating one attempt."""
    entitlements = await repository.live_for_users(session, user_ids, now=now)
    codes = await catalog.exam_codes_by_id(
        session, list({entitlement.exam_id for entitlement in entitlements})
    )
    grants_by_user: dict[uuid.UUID, list[LiveGrant]] = {}
    for entitlement in entitlements:
        grants_by_user.setdefault(entitlement.user_id, []).append(
            LiveGrant(
                exam_code=codes.get(entitlement.exam_id, ""),
                source=entitlement.source,
                ends_at=entitlement.ends_at,
            )
        )
    return grants_by_user
