"""Storage for candidate results. Append-only: a change is a new revision."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.results.models import (
    CandidateResultEvent,
    CandidateResultNotification,
    CandidateResultRevision,
)


async def latest_revision(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID, trainee_id: uuid.UUID
) -> CandidateResultRevision | None:
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
    row = CandidateResultRevision(
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
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def append_event(
    session: AsyncSession,
    *,
    revision_id: uuid.UUID,
    event_type: str,
    actor_user_id: uuid.UUID | None,
    idempotency_key: str,
) -> CandidateResultEvent:
    row = CandidateResultEvent(
        revision_id=revision_id,
        event_type=event_type,
        actor_user_id=actor_user_id,
        idempotency_key=idempotency_key,
    )
    session.add(row)
    await session.flush()
    # `at` is a server default, so without this the caller holds None and
    # cannot tell anybody when the event happened.
    await session.refresh(row)
    return row


async def queue_notification(
    session: AsyncSession,
    *,
    event_id: uuid.UUID,
    recipient: str,
    template_key: str,
    payload: dict[str, Any] | None,
    idempotency_key: str,
) -> CandidateResultNotification:
    row = CandidateResultNotification(
        event_id=event_id,
        recipient=recipient,
        template_key=template_key,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    session.add(row)
    await session.flush()
    return row


async def released_revision(
    session: AsyncSession, sitting_id: uuid.UUID, trainee_ids: list[uuid.UUID]
) -> CandidateResultRevision | None:
    """What a candidate may see: only a released revision, never a draft.

    Keyed by `trainees.id`, which is not the caller's `users.id`: a trainee is
    a roster entry with its own identity and a nullable link to an account.
    The route passed the user id straight in, so this matched nothing and
    every candidate was told their result was not released.
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

    The unique index makes a repeat write an error; this makes a repeat request
    an answer. A candidate tapping "I have read this" twice is not a conflict.
    """
    stmt = select(CandidateResultEvent).where(CandidateResultEvent.idempotency_key == idempotency_key)
    return (await session.execute(stmt)).scalar_one_or_none()
