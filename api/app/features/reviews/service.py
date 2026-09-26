"""Review use cases."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, raise_mapped
from app.features.reviews import domain, errors, repository
from app.features.reviews.models import GpLeadReview, SlotReview
from app.features.reviews.schemas import (
    CircuitReviewRead,
    GpLeadReviewRead,
    SlotReviewRead,
)
from app.features.rubrics import service_marking as rubrics
from app.features.sittings import service as sittings

_REFUSALS: dict[type[Exception], type[AppError]] = {
    domain.InvalidRag: errors.InvalidRagError,
    domain.InvalidStatus: errors.InvalidStatusError,
    domain.ReviewIncomplete: errors.ReviewIncompleteError,
    domain.NothingToReview: errors.NothingToReviewError,
    domain.ReviewConflict: errors.ReviewConflictError,
}


def _scored_domains(field_values: dict[str, Any]) -> set[str]:
    """Which domains a submission has rated. Field paths are `domain.score` or
    `domain.skill.score`."""
    return {key.split(".", 1)[0] for key in field_values if key.endswith(".score")}


async def _require_slot(session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID) -> None:
    """Every slot-addressed use case resolves the slot against the caller's org.

    Until this existed (P4), a write could store the caller's org beside
    another tenant's slot id — invisible to the slot's real owner.
    """
    if not await sittings.slot_is_in_org(session, org_id, slot_id):
        raise errors.SlotNotFound()


async def _required_domains(session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID) -> set[str]:
    """Which domains a completed review must have scored (R-1).

    All scoring domains on the sitting's bound rubric version.
    """
    version_id = await sittings.rubric_version_for_slot(session, org_id, slot_id)
    if version_id is None:
        return set()
    return await rubrics.reviewable_domains_for_version(session, org_id, version_id)


async def submit_slot_review(
    session: AsyncSession,
    org_id: uuid.UUID,
    slot_id: uuid.UUID,
    *,
    submitted_by: uuid.UUID,
    field_values: dict[str, Any],
    notes: str | None,
    status: str,
    observer_trainee_id: uuid.UUID | None,
    now: datetime,
) -> SlotReviewRead:
    """Submit or update one reviewer's own review of a slot."""
    await _require_slot(session, org_id, slot_id)
    required_domains = await _required_domains(session, org_id, slot_id)
    try:
        normalized = domain.normalize_status(status)
        for key, rating in field_values.items():
            if key.endswith(".score") and isinstance(rating, str):
                field_values[key] = domain.normalize_rag(rating)
        domain.ensure_completable(
            scored=_scored_domains(field_values), required=required_domains, status=normalized
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
    return _slot_read(slot_review)


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
    await _require_slot(session, org_id, slot_id)
    required_domains = await _required_domains(session, org_id, slot_id)
    existing = await repository.gp_lead_review(session, org_id, slot_id)
    try:
        domain.ensure_current(stored=existing.revision if existing else None, presented=presented_revision)
        normalized = domain.normalize_status(status)
        rag = domain.normalize_rag(overall_rag) if overall_rag else None
        domain.ensure_completable(
            scored=_scored_domains(field_values), required=required_domains, status=normalized
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
        overall_rag=rag,
        status=normalized,
        reviewed_by=reviewed_by,
        completed_at=now if normalized == "completed" else None,
    )
    return _gp_read(review)


async def read_gp_lead_review(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID
) -> GpLeadReviewRead:
    """The GP-lead review for this slot, or a refusal if none has been started."""
    review = await repository.gp_lead_review(session, org_id, slot_id)
    if review is None:
        raise errors.ReviewNotFound()
    return _gp_read(review)


async def finalize_circuit(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    merged_notes: str | None,
    finalized_by: uuid.UUID,
    now: datetime,
) -> CircuitReviewRead:
    """Finalise a supervisor's merged review for a whole circuit."""
    review = await repository.finalize_circuit_review(
        session,
        org_id,
        circuit_id=circuit_id,
        merged_notes=merged_notes,
        contributions=None,
        finalized_by=finalized_by,
        at=now,
    )
    return CircuitReviewRead(
        id=review.id,
        circuit_id=review.circuit_id,
        merged_notes=review.merged_notes,
        finalized_at=review.finalized_at,
    )


async def slot_has_review(session: AsyncSession, slot_id: uuid.UUID) -> bool:
    return await repository.slot_has_any_review(session, slot_id)


def _slot_read(slot_review: SlotReview) -> SlotReviewRead:
    """Map a stored slot review onto what a route returns."""
    return SlotReviewRead(
        id=slot_review.id,
        slot_id=slot_review.slot_id,
        submitted_by=slot_review.submitted_by,
        observer_trainee_id=slot_review.observer_trainee_id,
        status=slot_review.status,
        field_values=dict(slot_review.field_values or {}),
        notes=slot_review.notes,
        completed_at=slot_review.completed_at,
    )


def _gp_read(review: GpLeadReview) -> GpLeadReviewRead:
    """Map a stored GP-lead review onto what a route returns."""
    return GpLeadReviewRead(
        id=review.id,
        slot_id=review.slot_id,
        revision=review.revision,
        status=review.status,
        overall_rag=review.overall_rag,
        field_values=dict(review.field_values or {}),
        notes=review.notes,
        completed_at=review.completed_at,
    )


async def reviewed_slot_ids(session: AsyncSession, slot_ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
    """Which of these slots have been marked. For the console's slot list."""
    return await repository.slots_with_any_review(session, list(slot_ids))
