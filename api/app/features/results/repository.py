"""Storage for candidate results. Append-only: a change is a new revision."""

from __future__ import annotations

import uuid
from collections.abc import Collection, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import savepoint
from app.features.results import errors
from app.features.results.models import (
    CandidateResultEvent,
    CandidateResultRevision,
)

ERASED = "[erased]"
# The unique (sitting, trainee, revision) chain: the only violation that means "someone else saved first".
CHAIN_CONSTRAINT = "uq_candidate_result_revisions_chain"


async def latest_revision(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID, trainee_id: uuid.UUID
) -> CandidateResultRevision | None:
    """The most recent revision recorded for this candidate, whatever its workflow state."""
    stmt = (
        select(CandidateResultRevision)
        .where(
            CandidateResultRevision.org_id == org_id,
            CandidateResultRevision.sitting_id == sitting_id,
            CandidateResultRevision.trainee_id == trainee_id,
        )
        .order_by(CandidateResultRevision.revision.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def latest_revisions_for_sitting(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID
) -> list[CandidateResultRevision]:
    """The current revision for every candidate in a sitting, one row each."""
    stmt = (
        select(CandidateResultRevision)
        .where(CandidateResultRevision.org_id == org_id, CandidateResultRevision.sitting_id == sitting_id)
        .distinct(CandidateResultRevision.trainee_id)
        .order_by(CandidateResultRevision.trainee_id, CandidateResultRevision.revision.desc())
    )
    return list((await session.execute(stmt)).scalars())


async def append_revision(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
    revision: int,
    supersedes_revision: int | None,
    workflow_state: str,
    assessment_outcome: str | None,
    recruitment_outcome: str | None,
    rationale: str | None,
    moderation_notes: str | None,
    evidence_snapshot: dict[str, Any] | None,
    evidence_fingerprint: str,
    created_by: uuid.UUID,
    signed_off_by: uuid.UUID | None = None,
    signed_off_at: datetime | None = None,
    released_by: uuid.UUID | None = None,
    released_at: datetime | None = None,
) -> CandidateResultRevision:
    """Insert a new, append-only revision row: never edits one that already exists.

    Two presses that both read revision N both try to write N+1; the unique chain lets one in
    and the other is told the decision moved (409), not left to surface as a 500.
    """
    revision_row = CandidateResultRevision(
        org_id=org_id,
        sitting_id=sitting_id,
        trainee_id=trainee_id,
        revision=revision,
        supersedes_revision=supersedes_revision,
        workflow_state=workflow_state,
        assessment_outcome=assessment_outcome,
        recruitment_outcome=recruitment_outcome,
        rationale=rationale,
        moderation_notes=moderation_notes,
        evidence_snapshot=evidence_snapshot,
        evidence_fingerprint=evidence_fingerprint,
        created_by=created_by,
        signed_off_by=signed_off_by,
        signed_off_at=signed_off_at,
        released_by=released_by,
        released_at=released_at,
    )
    try:
        async with savepoint(session):
            session.add(revision_row)
            await session.flush()
    except IntegrityError as exc:
        if CHAIN_CONSTRAINT not in str(exc.orig):
            raise
        raise errors.DecisionRevisedError() from exc
    await session.refresh(revision_row)
    return revision_row


async def append_event(
    session: AsyncSession,
    *,
    revision_id: uuid.UUID,
    event_type: str,
    actor_user_id: uuid.UUID | None,
    idempotency_key: str,
) -> CandidateResultEvent:
    """Insert a record of something that happened to a decision, such as a sign-off."""
    event = CandidateResultEvent(
        revision_id=revision_id,
        event_type=event_type,
        actor_user_id=actor_user_id,
        idempotency_key=idempotency_key,
    )
    session.add(event)
    await session.flush()
    # `at` is a server default, so without this the caller holds None and
    # cannot tell anybody when the event happened.
    await session.refresh(event)
    return event


async def released_sitting_ids(
    session: AsyncSession,
    sitting_ids: Collection[uuid.UUID],
    trainee_ids: list[uuid.UUID],
    *,
    excluding_org_ids: Collection[uuid.UUID] = (),
) -> set[uuid.UUID]:
    """Of these sittings, the ones with a released revision for any of these roster entries,
    leaving out those organisations' sittings."""
    if not sitting_ids or not trainee_ids:
        return set()
    stmt = (
        select(CandidateResultRevision.sitting_id)
        .where(
            CandidateResultRevision.sitting_id.in_(list(sitting_ids)),
            CandidateResultRevision.trainee_id.in_(trainee_ids),
            CandidateResultRevision.workflow_state == "released",
            CandidateResultRevision.org_id.not_in(list(excluding_org_ids)),
        )
        .distinct()
    )
    return set((await session.execute(stmt)).scalars())


async def released_revision(
    session: AsyncSession, sitting_id: uuid.UUID, trainee_ids: list[uuid.UUID]
) -> CandidateResultRevision | None:
    """Only a released revision, never a draft — what a candidate may see.

    Keyed by `trainees.id`, not the caller's `users.id`: passing the user id
    straight in previously matched nothing, so every candidate was told their
    result was not released.
    """
    if not trainee_ids:
        return None
    stmt = (
        select(CandidateResultRevision)
        .where(
            CandidateResultRevision.sitting_id == sitting_id,
            CandidateResultRevision.trainee_id.in_(trainee_ids),
            CandidateResultRevision.workflow_state == "released",
        )
        .order_by(CandidateResultRevision.revision.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def event_by_idempotency_key(
    session: AsyncSession, idempotency_key: str
) -> CandidateResultEvent | None:
    """The event this key already wrote, if any.

    The unique index makes a repeat write an error; this makes a repeat request an answer.
    """
    stmt = select(CandidateResultEvent).where(CandidateResultEvent.idempotency_key == idempotency_key)
    return (await session.execute(stmt)).scalar_one_or_none()


async def released_outcomes(session: AsyncSession, org_id: uuid.UUID) -> list[tuple[uuid.UUID, str | None]]:
    """(sitting id, assessment outcome) of every candidate's current revision that has been released."""
    stmt = (
        select(CandidateResultRevision)
        .where(CandidateResultRevision.org_id == org_id)
        .distinct(CandidateResultRevision.sitting_id, CandidateResultRevision.trainee_id)
        .order_by(
            CandidateResultRevision.sitting_id,
            CandidateResultRevision.trainee_id,
            CandidateResultRevision.revision.desc(),
        )
    )
    rows = (await session.execute(stmt)).scalars()
    return [(row.sitting_id, row.assessment_outcome) for row in rows if row.released_at is not None]


async def current_decision_states(
    session: AsyncSession, org_id: uuid.UUID, sitting_ids: Sequence[uuid.UUID]
) -> list[tuple[uuid.UUID, uuid.UUID, str]]:
    """(sitting, trainee, workflow state) of each candidate's current revision.

    "Current" is the highest revision per (sitting, trainee), as in `released_outcomes`; a
    candidate with no revision has no row. Decisions are append-only, so rows may name a
    trainee no longer on any circuit: the caller decides who still counts.
    """
    stmt = (
        select(
            CandidateResultRevision.sitting_id,
            CandidateResultRevision.trainee_id,
            CandidateResultRevision.workflow_state,
        )
        .where(
            CandidateResultRevision.org_id == org_id,
            CandidateResultRevision.sitting_id.in_(list(sitting_ids)),
        )
        .distinct(CandidateResultRevision.sitting_id, CandidateResultRevision.trainee_id)
        .order_by(
            CandidateResultRevision.sitting_id,
            CandidateResultRevision.trainee_id,
            CandidateResultRevision.revision.desc(),
        )
    )
    return [
        (sitting_id, trainee_id, state)
        for sitting_id, trainee_id, state in (await session.execute(stmt)).all()
    ]


async def scrub_text_for_trainees(session: AsyncSession, trainee_ids: Sequence[uuid.UUID]) -> int:
    """Replace the free text on these candidates' decisions with `[erased]`; the one update the
    append-only trigger permits (S-20). Returns how many revisions had text to scrub."""
    if not trainee_ids:
        return 0
    result = await session.execute(
        update(CandidateResultRevision)
        .where(
            CandidateResultRevision.trainee_id.in_(list(trainee_ids)),
            or_(
                CandidateResultRevision.rationale.is_not(None),
                CandidateResultRevision.moderation_notes.is_not(None),
            ),
        )
        .values(
            rationale=case((CandidateResultRevision.rationale.is_(None), None), else_=ERASED),
            moderation_notes=case((CandidateResultRevision.moderation_notes.is_(None), None), else_=ERASED),
        )
        .execution_options(synchronize_session=False)
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]
