"""The one place that answers whether an attempt may start."""

from __future__ import annotations

import uuid
from collections.abc import Collection
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import service as catalog
from app.features.catalog.service import resolve_exam
from app.features.entitlements import domain, repository
from app.features.entitlements.errors import NotEntitled
from app.features.entitlements.models import Entitlement
from app.features.entitlements.schemas import EntitlementRead
from app.features.tenancy import service as tenancy

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
    held = await held_by_inactive_org(session, entitlements, now=now)
    return domain.decide(
        [_to_grant(entitlement) for entitlement in entitlements if entitlement.id not in held],
        now=now,
        trial=trial,
    )


async def held_by_inactive_org(
    session: AsyncSession, entitlements: Collection[Entitlement], *, now: datetime
) -> set[uuid.UUID]:
    """Ids of grants from an organisation that is suspended or past its contract (S-15): they open nothing."""
    inactive = await tenancy.inactive_org_ids(
        session,
        {entitlement.org_id for entitlement in entitlements if entitlement.org_id is not None},
        now=now,
    )
    return {entitlement.id for entitlement in entitlements if entitlement.org_id in inactive}


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


async def free_stations_left(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    exam_id: uuid.UUID,
    now: datetime,
    trial: domain.TrialState | None,
) -> int | None:
    """New stations the free trial still covers for this exam, or None when a live grant does.

    `trial` is None for somebody with no account to weigh, who then has none left.
    """
    decision = await decide(session, user_id=user_id, exam_id=exam_id, now=now)
    if decision.allowed:
        return None
    return domain.trial_stations_left(trial, now=now) if trial is not None else 0


async def grant(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    exam_code: str,
    source: str,
    source_ref: str | None = None,
    org_id: uuid.UUID | None = None,
    starts_at: datetime | None = None,
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
        starts_at=starts_at,
        ends_at=ends_at,
        granted_by=granted_by,
    )
    return _read(entitlement, exam.code, now=entitlement.starts_at)


async def running_purchases(
    session: AsyncSession, user_id: uuid.UUID, exam_code: str, *, now: datetime
) -> list[EntitlementRead]:
    """Paid-for access to this exam that has not ended: live now, or already bought to start later.

    Not refunded, not lapsed. A trial, an institution's grant or a lapsed purchase is not one
    (ADR 0012: entitlement is not payment).
    """
    return [
        grant
        for grant in await list_for_user(session, user_id, now=now)
        if grant.source == "purchase"
        and grant.exam_code == exam_code
        and grant.revoked_at is None
        and grant.ends_at is not None
        and grant.ends_at > now
    ]


async def revoked_ids(session: AsyncSession, entitlement_ids: Collection[uuid.UUID]) -> set[uuid.UUID]:
    """Which of these grants have been withdrawn."""
    return await repository.revoked_ids(session, entitlement_ids)


async def revoked_at(session: AsyncSession, entitlement_id: uuid.UUID) -> datetime | None:
    """When this grant was withdrawn, or None while it stands."""
    entitlement = await repository.by_id(session, entitlement_id)
    return entitlement.revoked_at if entitlement is not None else None


async def withdraw(session: AsyncSession, entitlement_id: uuid.UUID, *, now: datetime) -> None:
    """Take a grant back because the money for it went back (refund, dispute). No staff actor:
    the processor did it. Twice is once."""
    await repository.revoke(session, entitlement_id, at=now)


async def restore(session: AsyncSession, entitlement_id: uuid.UUID) -> None:
    """Give a withdrawn grant back because the money did not go back after all (a dispute won).
    Its window is unchanged, so it simply ends when it was always going to. A grant that has already
    run out stays out. Twice is once.

    Plans bought to follow it were pulled forward when it was withdrawn (`pull_stacked_purchases_forward`);
    they are pushed back behind it again, so the buyer keeps every day of both rather than losing the
    days the two windows would overlap."""
    if entitlement_id not in await repository.revoked_ids(session, [entitlement_id]):
        return
    await repository.restore(session, entitlement_id)
    restored = await repository.by_id(session, entitlement_id)
    if restored is None or restored.source != "purchase" or restored.ends_at is None:
        return
    cursor = restored.ends_at
    later_purchases = sorted(
        (
            later
            for later in await repository.for_user_and_exam(session, restored.user_id, restored.exam_id)
            if later.id != restored.id
            and later.source == "purchase"
            and later.revoked_at is None
            and later.ends_at is not None
            and later.starts_at >= restored.starts_at
        ),
        key=lambda grant: grant.starts_at,
    )
    for later in later_purchases:
        assert later.ends_at is not None
        if later.starts_at < cursor:
            shift = cursor - later.starts_at
            await repository.set_window(
                session, later.id, starts_at=later.starts_at + shift, ends_at=later.ends_at + shift
            )
            cursor = later.ends_at + shift
        else:
            cursor = later.ends_at


async def list_for_user(session: AsyncSession, user_id: uuid.UUID, *, now: datetime) -> list[EntitlementRead]:
    """Every grant this account has ever held, revoked and lapsed ones
    included, each with `live` computed against `now`.

    This is history, not access: a caller deciding what to show or allow
    must filter on `live` itself rather than assume every row here is current.

    Read once per session and moment: a request that asks twice (the station limit and the upgrade
    offer both do) is answered from `session.info`, which every write in `repository` clears.
    """
    memo: dict[tuple[uuid.UUID, datetime], list[EntitlementRead]] = session.info.setdefault(
        repository.MEMO_KEY, {}
    )
    if (user_id, now) in memo:
        return list(memo[(user_id, now)])
    entitlements = await repository.for_user(session, user_id)
    held = await held_by_inactive_org(session, entitlements, now=now)
    exam_ids = list({entitlement.exam_id for entitlement in entitlements})
    codes = await catalog.exam_codes_by_id(session, exam_ids)
    reads = []
    for entitlement in entitlements:
        read = _read(entitlement, codes.get(entitlement.exam_id, ""), now=now)
        reads.append(read.model_copy(update={"live": False}) if entitlement.id in held else read)
    memo[(user_id, now)] = reads
    return list(reads)


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


async def pull_stacked_purchases_forward(
    session: AsyncSession, withdrawn_id: uuid.UUID, *, now: datetime
) -> None:
    """A purchase was taken back: purchases bought to start where it ended start earlier by the
    time it no longer covers, so the buyer is not left with a gap before access they paid for."""
    withdrawn = await repository.by_id(session, withdrawn_id)
    if withdrawn is None or withdrawn.source != "purchase" or withdrawn.ends_at is None:
        return
    shift = withdrawn.ends_at - max(withdrawn.starts_at, now)
    if shift <= timedelta(0):
        return
    for later in await repository.for_user_and_exam(session, withdrawn.user_id, withdrawn.exam_id):
        if (
            later.id != withdrawn.id
            and later.source == "purchase"
            and later.revoked_at is None
            and later.ends_at is not None
            and later.starts_at >= withdrawn.ends_at
        ):
            await repository.set_window(
                session, later.id, starts_at=later.starts_at - shift, ends_at=later.ends_at - shift
            )
