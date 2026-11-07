"""Storage for appeals against a released result."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import savepoint
from app.features.results import errors
from app.features.results.models import CandidateResultRevision, ResultAppeal

LIVE = ("open", "in_review")
ERASED = "[erased]"
# The partial unique index: the only violation that means "an appeal is already open for this result".
ACTIVE_CONSTRAINT = "uq_result_appeals_active"


async def add(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
    revision: int,
    reason: str,
    requested_by: uuid.UUID,
    on_behalf: bool,
) -> ResultAppeal:
    """Insert an open appeal; a second live one for the same candidate and sitting is refused."""
    appeal = ResultAppeal(
        org_id=org_id,
        sitting_id=sitting_id,
        trainee_id=trainee_id,
        revision=revision,
        reason=reason,
        requested_by=requested_by,
        on_behalf=on_behalf,
    )
    try:
        async with savepoint(session):
            session.add(appeal)
            await session.flush()
    except IntegrityError as exc:
        if ACTIVE_CONSTRAINT not in str(exc.orig):
            raise
        raise errors.AppealAlreadyOpen() from exc
    await session.refresh(appeal)
    return appeal


async def locked(session: AsyncSession, org_id: uuid.UUID, appeal_id: uuid.UUID) -> ResultAppeal | None:
    """The appeal with its row locked, so two administrators deciding it serialise."""
    stmt = (
        select(ResultAppeal)
        .where(ResultAppeal.org_id == org_id, ResultAppeal.id == appeal_id)
        .with_for_update()
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def listed(session: AsyncSession, org_id: uuid.UUID, *, live: bool | None) -> list[ResultAppeal]:
    """Appeals of this organisation, oldest live first; `live` filters to waiting or decided ones."""
    stmt = select(ResultAppeal).where(ResultAppeal.org_id == org_id)
    if live is True:
        stmt = stmt.where(ResultAppeal.status.in_(LIVE)).order_by(ResultAppeal.created_at)
    else:
        if live is False:
            stmt = stmt.where(ResultAppeal.status.not_in(LIVE))
        stmt = stmt.order_by(ResultAppeal.created_at.desc())
    return list((await session.execute(stmt.limit(500))).scalars())


async def latest_for_candidate(
    session: AsyncSession, sitting_id: uuid.UUID, trainee_ids: Sequence[uuid.UUID]
) -> ResultAppeal | None:
    """The newest appeal any of these roster entries made on the sitting."""
    if not trainee_ids:
        return None
    stmt = (
        select(ResultAppeal)
        .where(ResultAppeal.sitting_id == sitting_id, ResultAppeal.trainee_id.in_(list(trainee_ids)))
        .order_by(ResultAppeal.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def live_for_trainee(session: AsyncSession, trainee_id: uuid.UUID) -> bool:
    """Whether this candidate has an appeal still open on any sitting."""
    stmt = select(ResultAppeal.id).where(ResultAppeal.trainee_id == trainee_id, ResultAppeal.status.in_(LIVE))
    return (await session.execute(stmt.limit(1))).first() is not None


async def revision_row(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID, trainee_id: uuid.UUID, revision: int
) -> CandidateResultRevision | None:
    """One numbered revision of a candidate's result: the one an appeal was asked against."""
    stmt = select(CandidateResultRevision).where(
        CandidateResultRevision.org_id == org_id,
        CandidateResultRevision.sitting_id == sitting_id,
        CandidateResultRevision.trainee_id == trainee_id,
        CandidateResultRevision.revision == revision,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def assign(session: AsyncSession, appeal: ResultAppeal, *, assignee: uuid.UUID, at: datetime) -> None:
    """Hand the appeal to a second marker and mark it as being reviewed."""
    appeal.status = "in_review"
    appeal.assigned_to = assignee
    appeal.assigned_at = at
    await session.flush()


async def settle(
    session: AsyncSession,
    appeal: ResultAppeal,
    *,
    status: str,
    decided_by: uuid.UUID,
    at: datetime,
    note: str | None,
    outcome_revision: int | None,
) -> None:
    """Close the appeal as resolved or declined, recording who decided, when and the revision it appended."""
    appeal.status = status
    appeal.decided_by = decided_by
    appeal.decided_at = at
    appeal.decision_note = note
    appeal.outcome_revision = outcome_revision
    await session.flush()


async def scrub_text_for_trainee(session: AsyncSession, trainee_id: uuid.UUID) -> int:
    """Replace the free text of this candidate's appeals with `[erased]`; the rows and outcomes stay."""
    result = await session.execute(
        update(ResultAppeal)
        .where(ResultAppeal.trainee_id == trainee_id, ResultAppeal.reason != ERASED)
        .values(
            reason=ERASED,
            decision_note=None,
        )
        .execution_options(synchronize_session=False)
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]
