"""Recording, signing off and releasing a candidate's outcome."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications import service as notifications
from app.features.results import domain, errors, repository
from app.features.results.models import CandidateResultRevision
from app.features.results.schemas import DecisionRead, TraineeResultRead

_REFUSALS: dict[type[Exception], type[Exception]] = {
    domain.IncompatibleOutcomes: errors.IncompatibleOutcomesError,
    domain.NotSignable: errors.NotSignableError,
    domain.InvalidWorkflow: errors.InvalidWorkflowError,
    domain.EvidenceChanged: errors.EvidenceChangedError,
}


def _raise(exc: Exception) -> None:
    raise _REFUSALS.get(type(exc), errors.InvalidWorkflowError)(str(exc)) from exc


async def save_draft(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
    assessment_outcome: str | None,
    recruitment_outcome: str | None,
    rationale: str | None,
    moderation_notes: str | None,
    evidence: dict[str, Any],
    actor_id: uuid.UUID,
) -> DecisionRead:
    """Record a decision without committing to it.

    A new revision rather than an edit: the table is append-only, so the history
    of what was considered survives.
    """
    latest = await repository.latest_revision(session, org_id, sitting_id, trainee_id)
    if latest and latest.workflow_state == "released":
        _raise(domain.InvalidWorkflow("A released result cannot be redrafted."))

    assessment = domain.Assessment(assessment_outcome) if assessment_outcome else None
    recruitment = domain.Recruitment(recruitment_outcome) if recruitment_outcome else None
    if assessment and recruitment:
        try:
            domain.ensure_compatible(assessment, recruitment)
        except domain.IncompatibleOutcomes as exc:
            _raise(exc)

    row = await repository.append_revision(
        session,
        org_id,
        sitting_id=sitting_id,
        trainee_id=trainee_id,
        revision=domain.next_revision(latest.revision if latest else None),
        supersedes_revision=latest.revision if latest else None,
        workflow_state=str(domain.Workflow.DRAFT),
        assessment_outcome=assessment_outcome,
        recruitment_outcome=recruitment_outcome,
        rationale=rationale,
        moderation_notes=moderation_notes,
        evidence_snapshot=evidence,
        evidence_fingerprint=domain.fingerprint(evidence),
        created_by=actor_id,
    )
    return _read(row)


async def sign_off(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
    actor_id: uuid.UUID,
    now: datetime,
) -> DecisionRead:
    latest = await _require(session, org_id, sitting_id, trainee_id)
    try:
        domain.transition(domain.Workflow(latest.workflow_state), domain.Workflow.SIGNED_OFF)
        assessment = domain.Assessment(latest.assessment_outcome) if latest.assessment_outcome else None
        domain.ensure_signable(assessment=assessment, rationale=latest.rationale)
    except Exception as exc:  # noqa: BLE001 - mapped above
        _raise(exc)

    row = await repository.append_revision(
        session,
        org_id,
        sitting_id=sitting_id,
        trainee_id=trainee_id,
        revision=domain.next_revision(latest.revision),
        supersedes_revision=latest.revision,
        workflow_state=str(domain.Workflow.SIGNED_OFF),
        assessment_outcome=latest.assessment_outcome,
        recruitment_outcome=latest.recruitment_outcome,
        rationale=latest.rationale,
        moderation_notes=latest.moderation_notes,
        evidence_snapshot=latest.evidence_snapshot,
        evidence_fingerprint=latest.evidence_fingerprint,
        created_by=actor_id,
        signed_off_by=actor_id,
        signed_off_at=now,
    )
    await repository.append_event(
        session,
        revision_id=row.id,
        event_type="signed_off",
        actor_user_id=actor_id,
        idempotency_key=f"signoff:{sitting_id}:{trainee_id}:{row.revision}",
    )
    return _read(row)


async def release(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
    recipient: str,
    current_evidence: dict[str, Any],
    actor_id: uuid.UUID,
    now: datetime,
) -> DecisionRead:
    """Send the outcome to the candidate.

    The evidence is re-checked: a station re-marked between sign-off and release
    would otherwise send someone an outcome nobody approved.
    """
    latest = await _require(session, org_id, sitting_id, trainee_id)
    try:
        domain.transition(domain.Workflow(latest.workflow_state), domain.Workflow.RELEASED)
        domain.ensure_evidence_unchanged(
            signed=latest.evidence_fingerprint, current=domain.fingerprint(current_evidence)
        )
    except Exception as exc:  # noqa: BLE001 - mapped above
        _raise(exc)

    row = await repository.append_revision(
        session,
        org_id,
        sitting_id=sitting_id,
        trainee_id=trainee_id,
        revision=domain.next_revision(latest.revision),
        supersedes_revision=latest.revision,
        workflow_state=str(domain.Workflow.RELEASED),
        assessment_outcome=latest.assessment_outcome,
        recruitment_outcome=latest.recruitment_outcome,
        rationale=latest.rationale,
        moderation_notes=latest.moderation_notes,
        evidence_snapshot=latest.evidence_snapshot,
        evidence_fingerprint=latest.evidence_fingerprint,
        created_by=actor_id,
        signed_off_by=latest.signed_off_by,
        signed_off_at=latest.signed_off_at,
        released_by=actor_id,
        released_at=now,
    )
    event = await repository.append_event(
        session,
        revision_id=row.id,
        event_type="released",
        actor_user_id=actor_id,
        idempotency_key=f"release:{sitting_id}:{trainee_id}",
    )
    # Queued on the shared outbox rather than sent inline, so a release is not
    # lost because a mail provider was briefly down. Written in this
    # transaction, so it cannot exist for a release that rolled back.
    await notifications.enqueue_email(
        session,
        recipient=recipient,
        subject="Your result is available",
        template_key="candidate_result_released",
        payload={"sitting_id": str(sitting_id)},
        idempotency_key=f"result_released:{sitting_id}:{trainee_id}",
    )
    _ = event
    return _read(row)


async def read_decision(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID, trainee_id: uuid.UUID
) -> DecisionRead:
    return _read(await _require(session, org_id, sitting_id, trainee_id))


async def read_my_result(
    session: AsyncSession, sitting_id: uuid.UUID, trainee_id: uuid.UUID
) -> TraineeResultRead:
    """What the candidate sees: released revisions only, and less of it.

    Moderation notes and the evidence snapshot stay internal. b2b's own schema
    doc says not to reproduce disclosure policy in frontend transforms, so the
    narrowing happens here.
    """
    row = await repository.released_revision(session, sitting_id, trainee_id)
    if row is None:
        raise errors.NotReleased()
    return TraineeResultRead(
        sitting_id=row.sitting_id,
        assessment_outcome=row.assessment_outcome,
        rationale=row.rationale,
        released_at=row.released_at,
    )


async def _require(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID, trainee_id: uuid.UUID
) -> CandidateResultRevision:
    row = await repository.latest_revision(session, org_id, sitting_id, trainee_id)
    if row is None:
        raise errors.ResultNotFound()
    return row


def _read(row: CandidateResultRevision) -> DecisionRead:
    return DecisionRead(
        revision=row.revision,
        workflow_state=row.workflow_state,
        assessment_outcome=row.assessment_outcome,
        recruitment_outcome=row.recruitment_outcome,
        rationale=row.rationale,
        signed_off_at=row.signed_off_at,
        released_at=row.released_at,
    )
