"""Review use cases."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.reviews import domain, errors, repository
from app.features.reviews.models import GpLeadReview, SlotReview
from app.features.reviews.schemas import (
    CircuitReviewRead,
    GpLeadReviewRead,
    SlotReviewRead,
)
from app.features.sittings import service as sittings

_REFUSALS: dict[type[Exception], type[Exception]] = {
    domain.InvalidRag: errors.InvalidRagError,
    domain.InvalidStatus: errors.InvalidStatusError,
    domain.ReviewIncomplete: errors.ReviewIncompleteError,
    domain.NothingToReview: errors.NothingToReviewError,
    domain.ReviewConflict: errors.ReviewConflictError,
}


def _raise(exc: Exception) -> None:
    raise _REFUSALS.get(type(exc), errors.InvalidStatusError)(str(exc)) from exc


def _scored_domains(field_values: dict[str, Any]) -> set[str]:
    """Which domains a submission has rated.

    Field paths are `domain.score` or `domain.skill.score`, as b2b writes them.
    """
    return {key.split(".", 1)[0] for key in field_values if key.endswith(".score")}


async def _require_slot(session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID) -> None:
    """Every slot-addressed use case resolves the slot against the caller's org.

    The org comes from the path and the slot from the URL, and until this
    existed nothing compared them (P4). Reads happened to be safe because they
    filter on `org_id`; writes stored the caller's org beside another tenant's
    slot id, which kept it invisible to the slot's real owner and so looked
    contained.
    """
    if not await sittings.slot_is_in_org(session, org_id, slot_id):
        raise errors.SlotNotFound()


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
    required_domains: set[str],
    now: datetime,
) -> SlotReviewRead:
    await _require_slot(session, org_id, slot_id)
    try:
        normalized = domain.normalize_status(status)
        for key, value in field_values.items():
            if key.endswith(".score") and isinstance(value, str):
                field_values[key] = domain.normalize_rag(value)
        domain.ensure_completable(
            scored=_scored_domains(field_values), required=required_domains, status=normalized
        )
    except Exception as exc:  # noqa: BLE001 - mapped above
        _raise(exc)

    row = await repository.upsert_slot_review(
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
    return _slot_read(row)


async def read_slot_reviews(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID
) -> list[SlotReviewRead]:
    return [_slot_read(r) for r in await repository.slot_reviews(session, org_id, slot_id)]


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
    required_domains: set[str],
    now: datetime,
) -> GpLeadReviewRead:
    await _require_slot(session, org_id, slot_id)
    existing = await repository.gp_lead_review(session, org_id, slot_id)
    try:
        domain.ensure_current(stored=existing.revision if existing else None, presented=presented_revision)
        normalized = domain.normalize_status(status)
        rag = domain.normalize_rag(overall_rag) if overall_rag else None
        domain.ensure_completable(
            scored=_scored_domains(field_values), required=required_domains, status=normalized
        )
    except Exception as exc:  # noqa: BLE001 - mapped above
        _raise(exc)

    row = await repository.save_gp_lead_review(
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
    return _gp_read(row)


async def read_gp_lead_review(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID
) -> GpLeadReviewRead:
    row = await repository.gp_lead_review(session, org_id, slot_id)
    if row is None:
        raise errors.ReviewNotFound()
    return _gp_read(row)


async def finalize_circuit(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    merged_notes: str | None,
    finalized_by: uuid.UUID,
    now: datetime,
) -> CircuitReviewRead:
    row = await repository.finalize_circuit_review(
        session,
        org_id,
        circuit_id=circuit_id,
        merged_notes=merged_notes,
        contributions=None,
        finalized_by=finalized_by,
        at=now,
    )
    return CircuitReviewRead(
        id=row.id,
        circuit_id=row.circuit_id,
        merged_notes=row.merged_notes,
        finalized_at=row.finalized_at,
    )


async def slot_has_review(session: AsyncSession, slot_id: uuid.UUID) -> bool:
    return await repository.slot_has_any_review(session, slot_id)


def _slot_read(row: SlotReview) -> SlotReviewRead:
    return SlotReviewRead(
        id=row.id,
        slot_id=row.slot_id,
        submitted_by=row.submitted_by,
        observer_trainee_id=row.observer_trainee_id,
        status=row.status,
        field_values=dict(row.field_values or {}),
        notes=row.notes,
        completed_at=row.completed_at,
    )


def _gp_read(row: GpLeadReview) -> GpLeadReviewRead:
    return GpLeadReviewRead(
        id=row.id,
        slot_id=row.slot_id,
        revision=row.revision,
        status=row.status,
        overall_rag=row.overall_rag,
        field_values=dict(row.field_values or {}),
        notes=row.notes,
        completed_at=row.completed_at,
    )
