"""Review use cases."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.errors import AppError, raise_mapped
from app.core.role_policy import policy
from app.core.schemas import ReviewFormRead
from app.features.attempts import service_platform_actions as attempts_actions
from app.features.reviews import domain, errors, repository
from app.features.reviews.models import CircuitReview, GpLeadReview, SlotReview
from app.features.reviews.schemas import (
    CircuitReviewRead,
    GpLeadReviewRead,
    MarkingRetryRead,
    SlotReviewRead,
)
from app.features.roster import service as roster
from app.features.rubrics import service_marking as rubrics
from app.features.rubrics import service_scoring as rubric_scoring
from app.features.sittings import service as sittings
from app.features.sittings import service_reads as sittings_reads

_REFUSALS: dict[type[Exception], type[AppError]] = {
    rubric_scoring.InvalidRating: errors.InvalidRatingError,
    domain.InvalidVerdict: errors.InvalidRatingError,
    domain.InvalidStatus: errors.InvalidStatusError,
    domain.ReviewIncomplete: errors.ReviewIncompleteError,
    domain.NothingToReview: errors.NothingToReviewError,
    domain.ReviewConflict: errors.ReviewConflictError,
}


def _scored_domains(
    structure: rubric_scoring.RubricStructure | None, field_values: dict[str, Any]
) -> set[str]:
    """Which domains a submission has rated: paths `domain.<rating field>` or
    `domain.skill.<rating field>` that hold a value."""
    if structure is None:
        return set()
    scored: set[str] = set()
    for path, value in field_values.items():
        parts = rubric_scoring.rating_path_parts(structure, path)
        if parts is not None and value is not None:
            scored.add(parts[0])
    return scored


def _normalised_ratings(
    structure: rubric_scoring.RubricStructure | None, field_values: dict[str, Any]
) -> dict[str, Any]:
    """The submission with every rating path checked against the rubric's native rating.

    " g " becomes "G" on an R/A/G rubric and "7" becomes 7 on a 0-10 one;
    anything that is not a rating on this rubric raises `InvalidRating`
    (422 `invalid_rating`). A null clears a rating in a draft. Other paths
    (free-text notes a form may add) pass through untouched.
    """
    if structure is None:
        return dict(field_values)
    normalised: dict[str, Any] = {}
    for path, value in field_values.items():
        if value is not None and rubric_scoring.rating_path_parts(structure, path) is not None:
            value = rubric_scoring.normalise_rating(structure, value)
        normalised[path] = value
    return normalised


async def _require_slot(session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID) -> None:
    """Every slot-addressed use case resolves the slot against the caller's org.

    Until this existed (P4), a write could store the caller's org beside
    another tenant's slot id — invisible to the slot's real owner.
    """
    if not await sittings.slot_is_in_org(session, org_id, slot_id):
        raise errors.SlotNotFound()


async def retry_slot_marking(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID, *, actor: Principal, now: datetime
) -> MarkingRetryRead:
    """Queue the automatic marking of this slot's attempt again, after it failed."""
    await _require_slot(session, org_id, slot_id)
    queued = await attempts_actions.rescore_slot_attempt(session, org_id, slot_id, actor=actor, now=now)
    return MarkingRetryRead(queued=queued.queued, policy_version=queued.policy_version, reason=queued.reason)


async def _require_open_slot(session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID) -> None:
    """A slot whose reviews may still change: refused once the candidate's decision for the
    sitting is signed off or released, since that decision (and what the candidate reads)
    was made on these reviews. Redrafting a signed-off decision reopens them (R-4).
    """
    await _require_slot(session, org_id, slot_id)
    found = await sittings_reads.slot_and_sitting(session, org_id, slot_id)
    if found is None:
        return
    slot, sitting = found
    await _ensure_unsettled(session, org_id, sitting, [slot])


async def _ensure_unsettled(
    session: AsyncSession,
    org_id: uuid.UUID,
    sitting: sittings_reads.SittingRef,
    slots: Sequence[sittings_reads.SlotRef],
) -> None:
    """Refuse a change to reviews a signed-off or released decision was made on."""
    # `results` imports this slice, so its import has to wait until call time.
    from app.features.results import service as results

    if await results.decision_settled(session, org_id, sitting=sitting, slots=slots):
        raise errors.ReviewLockedError()


def _ensure_reviewer(*, reviewer_id: uuid.UUID, role: str | None, supervisor_id: uuid.UUID | None) -> None:
    """An institution administrator reviews any slot of theirs; a supervisor only the circuits
    they are named on (R-9). The same people who may read the transcript (`attempts.service_access`).
    """
    if policy("is_institution_admin")(role):
        return
    if supervisor_id is None or supervisor_id != reviewer_id:
        raise errors.NotReviewerError()


async def slot_rubric(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID
) -> rubrics.ScoringRubric | None:
    """The rubric a slot's reviews are checked and scored by: its sitting's bound version."""
    version_id = await sittings.rubric_version_for_slot(session, org_id, slot_id)
    if version_id is None:
        return None
    return await rubrics.scoring_rubric_for_version(session, org_id, version_id)


def _required_domains(scoring_rubric: rubrics.ScoringRubric | None) -> dict[str, str]:
    """Which domains a completed review must have rated (R-1): every scoring domain, id to title."""
    if scoring_rubric is None:
        return {}
    structure = scoring_rubric.structure
    scoring = rubric_scoring.scoring_domain_ids(structure)
    return {section.id: section.title or section.id for section in structure.domains if section.id in scoring}


def review_form(scoring_rubric: rubrics.ScoringRubric | None) -> ReviewFormRead | None:
    """What a reviewer can rate on a slot, or None when the slot has no rubric."""
    return rubrics.review_form(scoring_rubric) if scoring_rubric else None


async def submit_slot_review(
    session: AsyncSession,
    org_id: uuid.UUID,
    slot_id: uuid.UUID,
    *,
    submitted_by: uuid.UUID,
    role: str | None,
    field_values: dict[str, Any],
    notes: str | None,
    status: str,
    observer_trainee_id: uuid.UUID | None,
    now: datetime,
) -> SlotReviewRead:
    """Submit or update one reviewer's own review of a slot.

    `observer_trainee_id` (a peer who watched) must be one of this organisation's roster entries.
    """
    await _require_open_slot(session, org_id, slot_id)
    _ensure_reviewer(
        reviewer_id=submitted_by,
        role=role,
        supervisor_id=await sittings_reads.supervisor_for_slot(session, org_id, slot_id),
    )
    if observer_trainee_id is not None:
        await roster.ensure_trainee(session, org_id, observer_trainee_id)
    scoring_rubric = await slot_rubric(session, org_id, slot_id)
    structure = scoring_rubric.structure if scoring_rubric else None
    try:
        normalized = domain.normalize_status(status)
        field_values = _normalised_ratings(structure, field_values)
        domain.ensure_completable(
            scored=_scored_domains(structure, field_values),
            required=_required_domains(scoring_rubric),
            status=normalized,
        )
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)

    slot_review = await repository.upsert_slot_review(
        session,
        org_id,
        slot_id=slot_id,
        submitted_by=submitted_by,
        observer_trainee_id=observer_trainee_id,
        field_values=field_values,
        notes=notes,
        status=normalized,
        completed_at=now if normalized == "completed" else None,
    )
    return _slot_read(slot_review, form=review_form(scoring_rubric))


async def save_gp_lead_review(
    session: AsyncSession,
    org_id: uuid.UUID,
    slot_id: uuid.UUID,
    *,
    presented_revision: int,
    field_values: dict[str, Any],
    notes: str | None,
    overall_rag: str | None,
    status: str,
    reviewed_by: uuid.UUID,
    now: datetime,
) -> GpLeadReviewRead:
    """Save the GP-lead review for a slot, refusing a save against a stale revision."""
    await _require_open_slot(session, org_id, slot_id)
    scoring_rubric = await slot_rubric(session, org_id, slot_id)
    structure = scoring_rubric.structure if scoring_rubric else None
    existing = await repository.gp_lead_review(session, org_id, slot_id)
    try:
        domain.ensure_current(stored=existing.revision if existing else None, presented=presented_revision)
        normalized = domain.normalize_status(status)
        verdict = domain.normalize_verdict(overall_rag) if overall_rag else None
        field_values = _normalised_ratings(structure, field_values)
        domain.ensure_completable(
            scored=_scored_domains(structure, field_values),
            required=_required_domains(scoring_rubric),
            status=normalized,
        )
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)

    review = await repository.save_gp_lead_review(
        session,
        org_id,
        slot_id=slot_id,
        revision=domain.next_revision(existing.revision if existing else None),
        field_values=field_values,
        notes=notes,
        overall_rag=verdict,
        status=normalized,
        reviewed_by=reviewed_by,
        completed_at=now if normalized == "completed" else None,
    )
    return _gp_read(review, form=review_form(scoring_rubric))


async def read_gp_lead_review(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID
) -> GpLeadReviewRead | None:
    """The GP-lead review for this slot, or `None` before anybody has started one."""
    review = await repository.gp_lead_review(session, org_id, slot_id)
    if review is None:
        return None
    return _gp_read(review, form=review_form(await slot_rubric(session, org_id, slot_id)))


async def finalize_circuit(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    merged_notes: str | None,
    finalized_by: uuid.UUID,
    role: str | None,
    now: datetime,
) -> CircuitReviewRead:
    """Finalise a supervisor's merged review for a whole circuit, once (R-10).

    The circuit must be this organisation's, the caller its named supervisor or an
    institution administrator, and no candidate on it may have a decision signed off
    or released: that decision was made without these notes.
    """
    detail = await sittings_reads.circuit_detail(session, org_id, circuit_id)
    if detail is None:
        raise errors.CircuitNotFound()
    _ensure_reviewer(reviewer_id=finalized_by, role=role, supervisor_id=detail.circuit.supervisor_user_id)
    if await repository.circuit_review(session, org_id, circuit_id) is not None:
        raise errors.CircuitReviewFinalizedError()
    await _ensure_unsettled(session, org_id, detail.sitting, detail.slots)
    review = await repository.finalize_circuit_review(
        session,
        org_id,
        circuit_id=circuit_id,
        merged_notes=merged_notes,
        contributions=None,
        finalized_by=finalized_by,
        at=now,
    )
    return _circuit_read(review)


async def read_circuit_review(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID
) -> CircuitReviewRead | None:
    """Whether a circuit's merged review has been finalised, by whom and when.

    `None` until somebody finalises it: "no review yet" is an ordinary state of
    a circuit, not an error, and it lets a screen tell "not yet published" apart
    from a published review with no notes without a 404 in every console.
    """
    review = await repository.circuit_review(session, org_id, circuit_id)
    return None if review is None else _circuit_read(review)


async def read_my_slot_review(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID, *, submitted_by: uuid.UUID
) -> SlotReviewRead | None:
    """The caller's own review of this slot, so an examiner can pick up a draft
    where they left it. `None` when they have not started one; the slot itself must exist.
    """
    await _require_slot(session, org_id, slot_id)
    review = await repository.slot_review_for(session, org_id, slot_id, submitted_by)
    if review is None:
        return None
    return _slot_read(review, form=review_form(await slot_rubric(session, org_id, slot_id)))


async def slot_has_review(session: AsyncSession, slot_id: uuid.UUID) -> bool:
    return await repository.slot_has_any_review(session, slot_id)


def _slot_read(slot_review: SlotReview, *, form: ReviewFormRead | None = None) -> SlotReviewRead:
    """Map a stored slot review onto what a route returns, with the form it was rated on."""
    return SlotReviewRead(
        id=slot_review.id,
        slot_id=slot_review.slot_id,
        submitted_by=slot_review.submitted_by,
        observer_trainee_id=slot_review.observer_trainee_id,
        status=slot_review.status,
        field_values=dict(slot_review.field_values or {}),
        notes=slot_review.notes,
        completed_at=slot_review.completed_at,
        form=form,
    )


def _circuit_read(review: CircuitReview) -> CircuitReviewRead:
    """Map a stored circuit review onto what a route returns."""
    return CircuitReviewRead(
        id=review.id,
        circuit_id=review.circuit_id,
        merged_notes=review.merged_notes,
        finalized_at=review.finalized_at,
        finalized_by=review.finalized_by,
    )


def _gp_read(review: GpLeadReview, *, form: ReviewFormRead | None) -> GpLeadReviewRead:
    """Map a stored GP-lead review onto what a route returns, with the form it was rated on."""
    return GpLeadReviewRead(
        id=review.id,
        slot_id=review.slot_id,
        revision=review.revision,
        status=review.status,
        overall_rag=review.overall_rag,
        field_values=dict(review.field_values or {}),
        notes=review.notes,
        completed_at=review.completed_at,
        form=form,
    )


async def reviewed_slot_ids(session: AsyncSession, slot_ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
    """Which of these slots have been marked. For the console's slot list."""
    return await repository.slots_with_any_review(session, list(slot_ids))
