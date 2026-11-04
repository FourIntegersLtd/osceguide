"""Recording, signing off and releasing a candidate's outcome."""

from __future__ import annotations

import uuid
from collections.abc import Collection, Mapping, Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, raise_mapped
from app.features.notifications import service as notifications
from app.features.results import domain, errors, repository, service_evidence
from app.features.results.models import CandidateResultRevision
from app.features.results.schemas import (
    BulkReleaseCandidate,
    BulkReleaseResult,
    DecisionRead,
    ReleasedCandidate,
    SkippedRelease,
)
from app.features.reviews import service_summary as reviews
from app.features.roster import service as roster
from app.features.sittings import service_reads as sittings
from app.features.tenancy import service as tenancy

_REFUSALS: dict[type[Exception], type[AppError]] = {
    domain.IncompatibleOutcomes: errors.IncompatibleOutcomesError,
    domain.NotSignable: errors.NotSignableError,
    domain.InvalidWorkflow: errors.InvalidWorkflowError,
    domain.EvidenceChanged: errors.EvidenceChangedError,
    domain.NotReleasable: errors.NotReleasableError,
    domain.RecruitmentOutsideExam: errors.RecruitmentOutsideExamError,
    domain.DecisionOutsideExam: errors.DecisionOutsideExamError,
    domain.CandidateDidNotSit: errors.CandidateDidNotSitError,
}


async def _ensure_recruitment_allowed(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID, recruitment: domain.Recruitment
) -> None:
    """A recruitment outcome belongs to an exam-mode (hire) sitting only."""
    sitting = await sittings.sitting_ref(session, org_id, sitting_id)
    if sitting is None:
        raise errors.SittingNotFound()
    try:
        domain.ensure_recruitment_allowed(sitting.mode, recruitment)
    except domain.RecruitmentOutsideExam as exc:
        raise_mapped(exc, _REFUSALS)


async def _ensure_decidable(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID, user_id: uuid.UUID | None
) -> None:
    """An exam sitting, and a candidate who sat at least one station on it (R-11).

    A slot names its candidate by `users.id`, so a roster entry nobody has
    signed in as yet has sat nothing.
    """
    sitting = await sittings.sitting_ref(session, org_id, sitting_id)
    if sitting is None:
        raise errors.SittingNotFound()
    slots = await sittings.slots_for_sitting(session, org_id, sitting_id)
    sat = user_id is not None and any(
        slot.trainee_id == user_id and slot.status in sittings.SAT_SLOT_STATUSES for slot in slots
    )
    try:
        domain.ensure_decidable(sitting_mode=sitting.mode, sat_a_station=sat)
    except domain.NotDecidable as exc:
        raise_mapped(exc, _REFUSALS)


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
    expected_revision: int,
    actor_id: uuid.UUID,
) -> DecisionRead:
    """Record a decision without committing to it: a new revision, not an edit.

    `expected_revision` guards a draft against two screens saving from the same
    read; a stale save is refused rather than silently superseding a newer one.
    """
    # Before anything is written: the foreign key would catch a bad id, but as
    # an unhandled integrity error rather than a refusal the caller can read.
    trainee = await roster.read_trainee(session, org_id, trainee_id)
    await _ensure_decidable(session, org_id, sitting_id, trainee.user_id)

    latest = await repository.latest_revision(session, org_id, sitting_id, trainee_id)
    if latest and latest.workflow_state == "released":
        raise_mapped(domain.InvalidWorkflow("A released result cannot be redrafted."), _REFUSALS)

    try:
        domain.ensure_current(stored=latest.revision if latest else None, presented=expected_revision)
    except domain.StaleDecision as exc:
        raise errors.DecisionRevisedError(
            str(exc), details={"current_revision": latest.revision if latest else 0}
        ) from exc

    evidence = await service_evidence.current_evidence(session, org_id, sitting_id, trainee_id)
    assessment = domain.Assessment(assessment_outcome) if assessment_outcome else None
    recruitment = domain.Recruitment(recruitment_outcome) if recruitment_outcome else None
    if recruitment is not None:
        await _ensure_recruitment_allowed(session, org_id, sitting_id, recruitment)
    if assessment and recruitment:
        try:
            domain.ensure_compatible(assessment, recruitment)
        except domain.IncompatibleOutcomes as exc:
            raise_mapped(exc, _REFUSALS)

    revision_row = await repository.append_revision(
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
    return _read(revision_row)


async def sign_off(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
    actor_id: uuid.UUID,
    now: datetime,
) -> DecisionRead:
    """Put a name to the current draft. Refused if it has no outcome or rationale yet."""
    latest = await _require(session, org_id, sitting_id, trainee_id)
    current = await service_evidence.current_evidence(
        session, org_id, sitting_id, trainee_id, stored=latest.evidence_snapshot
    )
    if await reviews.slots_with_pending_reviews(
        session, org_id, [uuid.UUID(station["slot_id"]) for station in current["stations"]]
    ):
        raise errors.ReviewsPendingError()
    try:
        domain.transition(domain.Workflow(latest.workflow_state), domain.Workflow.SIGNED_OFF)
        assessment = domain.Assessment(latest.assessment_outcome) if latest.assessment_outcome else None
        domain.ensure_signable(assessment=assessment, rationale=latest.rationale)
        # R-40: a station re-marked since the draft is refused here, not at release.
        domain.ensure_evidence_unchanged(
            signed=latest.evidence_fingerprint, current=domain.fingerprint(current)
        )
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)

    revision_row = await repository.append_revision(
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
        revision_id=revision_row.id,
        event_type="signed_off",
        actor_user_id=actor_id,
        idempotency_key=f"signoff:{sitting_id}:{trainee_id}:{revision_row.revision}",
    )
    return _read(revision_row)


async def release(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
    actor_id: uuid.UUID,
    now: datetime,
) -> DecisionRead:
    """Send the outcome to the candidate.

    The evidence is re-checked: a station re-marked between sign-off and release
    would otherwise send someone an outcome nobody approved.

    The recipient is looked up here rather than passed in — the router previously
    supplied `principal.email`, so every release notified the administrator who
    pressed the button and never the candidate.
    """
    latest = await _require(session, org_id, sitting_id, trainee_id)
    current = await service_evidence.current_evidence(
        session, org_id, sitting_id, trainee_id, stored=latest.evidence_snapshot
    )
    try:
        domain.transition(domain.Workflow(latest.workflow_state), domain.Workflow.RELEASED)
        domain.ensure_releasable(latest.assessment_outcome)
        domain.ensure_evidence_unchanged(
            signed=latest.evidence_fingerprint, current=domain.fingerprint(current)
        )
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)
    # Looked up before anything is written, so every refusal comes ahead of the
    # first write and a bulk release can skip this candidate cleanly.
    recipient = await roster.trainee_email(session, org_id, trainee_id)
    org = await tenancy.org_ref_by_id(session, org_id)
    if org is None:
        raise errors.ResultNotFound()

    revision_row = await repository.append_revision(
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
    await repository.append_event(
        session,
        revision_id=revision_row.id,
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
        payload={"sitting_id": str(sitting_id), "org_slug": org.slug, "org_name": org.name},
        idempotency_key=f"result_released:{sitting_id}:{trainee_id}",
    )
    return _read(revision_row)


async def release_many(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    sitting_id: uuid.UUID,
    candidates: list[BulkReleaseCandidate],
    actor_id: uuid.UUID,
    now: datetime,
) -> BulkReleaseResult:
    """Release several candidates' outcomes from one button press.

    Each candidate goes through `release` exactly as the single route does, so
    each gets their own evidence check and their own email. A candidate who is
    refused is reported and skipped rather than failing the rest: `release`
    raises every refusal before it writes anything.
    """
    outcome = BulkReleaseResult()
    for candidate in candidates:
        try:
            decision = await release(
                session,
                org_id,
                sitting_id=sitting_id,
                trainee_id=candidate.trainee_id,
                actor_id=actor_id,
                now=now,
            )
        except AppError as refusal:
            outcome.skipped.append(SkippedRelease(trainee_id=candidate.trainee_id, code=refusal.code))
            continue
        outcome.released.append(ReleasedCandidate(trainee_id=candidate.trainee_id, decision=decision))
    return outcome


async def sitting_has_settled_decision(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID
) -> bool:
    """Whether any candidate's current decision on this sitting is signed off or released.

    Asked by `sittings` before it puts anybody new into the sitting (R-7).
    """
    latest = await repository.latest_revisions_for_sitting(session, org_id, sitting_id)
    return any(row.workflow_state != domain.Workflow.DRAFT for row in latest)


async def decision_settled(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    sitting: sittings.SittingRef,
    slots: Sequence[sittings.SlotRef],
) -> bool:
    """Whether any of these slots' candidates has a current decision signed off or released.

    Asked by `reviews` before a review changes, or a circuit's review is finalised: the
    decision was made on those reviews. A slot names a `users.id`; the decision a `trainees.id`.
    """
    user_ids = list({slot.trainee_id for slot in slots})
    trainees = await roster.trainees_by_user_id(session, org_id, user_ids)
    for trainee in trainees.values():
        latest = await repository.latest_revision(session, org_id, sitting.id, trainee.id)
        if latest is not None and latest.workflow_state != domain.Workflow.DRAFT:
            return True
    return False


async def read_decision(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID, trainee_id: uuid.UUID
) -> DecisionRead | None:
    """The current revision, or `None` before anybody has recorded one."""
    revision_row = await repository.latest_revision(session, org_id, sitting_id, trainee_id)
    return None if revision_row is None else _read(revision_row)


async def _require(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID, trainee_id: uuid.UUID
) -> CandidateResultRevision:
    """The current revision for this candidate, or the refusal if nothing has been recorded."""
    revision_row = await repository.latest_revision(session, org_id, sitting_id, trainee_id)
    if revision_row is None:
        raise errors.ResultNotFound()
    return revision_row


def _read(revision_row: CandidateResultRevision) -> DecisionRead:
    """Map a stored revision onto what a route returns."""
    return DecisionRead(
        revision=revision_row.revision,
        workflow_state=revision_row.workflow_state,
        assessment_outcome=revision_row.assessment_outcome,
        recruitment_outcome=revision_row.recruitment_outcome,
        rationale=revision_row.rationale,
        signed_off_at=revision_row.signed_off_at,
        released_at=revision_row.released_at,
    )


async def decisions_for_sitting(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID
) -> dict[uuid.UUID, DecisionRead]:
    """Every candidate's current decision, keyed by `trainees.id`. For the sitting report."""
    revisions = await repository.latest_revisions_for_sitting(session, org_id, sitting_id)
    return {revision_row.trainee_id: _read(revision_row) for revision_row in revisions}


async def released_outcomes_by_sitting(
    session: AsyncSession, org_id: uuid.UUID
) -> dict[uuid.UUID, list[str | None]]:
    """Every released decision's outcome, grouped by sitting. For reporting across sittings."""
    grouped: dict[uuid.UUID, list[str | None]] = {}
    for sitting_id, outcome in await repository.released_outcomes(session, org_id):
        grouped.setdefault(sitting_id, []).append(outcome)
    return grouped


async def decision_counts(
    session: AsyncSession,
    org_id: uuid.UUID,
    candidates: Mapping[uuid.UUID, Collection[uuid.UUID]],
) -> dict[uuid.UUID, dict[str, int]]:
    """Per sitting, the given candidates (roster ids) by the workflow state of their current decision.

    A decision outlives its candidate's place on a circuit, so only `candidates` are counted.
    For the results index.
    """
    counts: dict[uuid.UUID, dict[str, int]] = {}
    for sitting_id, trainee_id, state in await repository.current_decision_states(
        session, org_id, list(candidates)
    ):
        if trainee_id in candidates[sitting_id]:
            stages = counts.setdefault(sitting_id, {})
            stages[state] = stages.get(state, 0) + 1
    return counts


async def erase_text_for_user(session: AsyncSession, *, user_id: uuid.UUID) -> int:
    """An account is being erased: what was written about them in a decision becomes `[erased]`.

    Who decided, when and the outcome stay; the free text names the person and does not.
    """
    trainee_ids = await roster.trainee_ids_for_user(session, user_id)
    return await repository.scrub_text_for_trainees(session, trainee_ids)
