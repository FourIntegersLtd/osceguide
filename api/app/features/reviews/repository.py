"""Storage for the three kinds of human review."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.reviews.models import CircuitReview, GpLeadReview, SlotReview


async def slot_review_for(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID, submitted_by: uuid.UUID
) -> SlotReview | None:
    """This reviewer's own review of this slot, or None if they have not submitted one."""
    stmt = select(SlotReview).where(
        SlotReview.org_id == org_id,
        SlotReview.slot_id == slot_id,
        SlotReview.submitted_by == submitted_by,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def slot_reviews(session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID) -> list[SlotReview]:
    """Every review of this slot, oldest first."""
    stmt = (
        select(SlotReview)
        .where(SlotReview.org_id == org_id, SlotReview.slot_id == slot_id)
        .order_by(SlotReview.created_at)
    )
    return list((await session.execute(stmt)).scalars())


async def slot_reviews_for_slots(
    session: AsyncSession, org_id: uuid.UUID, slot_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[SlotReview]]:
    """Every review of each slot, in one query, oldest first within a slot."""
    if not slot_ids:
        return {}
    stmt = (
        select(SlotReview)
        .where(SlotReview.org_id == org_id, SlotReview.slot_id.in_(list(slot_ids)))
        .order_by(SlotReview.created_at)
    )
    reviews_by_slot: dict[uuid.UUID, list[SlotReview]] = {slot_id: [] for slot_id in slot_ids}
    for review in (await session.execute(stmt)).scalars():
        reviews_by_slot[review.slot_id].append(review)
    return reviews_by_slot


async def upsert_slot_review(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    slot_id: uuid.UUID,
    submitted_by: uuid.UUID,
    observer_trainee_id: uuid.UUID | None,
    field_values: dict[str, Any],
    notes: str | None,
    status: str,
    completed_at: datetime | None,
) -> SlotReview:
    """Create this reviewer's review of this slot, or update it if they already have one."""
    existing = await slot_review_for(session, org_id, slot_id, submitted_by)
    if existing is None:
        slot_review = SlotReview(
            org_id=org_id,
            slot_id=slot_id,
            submitted_by=submitted_by,
            observer_trainee_id=observer_trainee_id,
            field_values=field_values,
            notes=notes,
            status=status,
            completed_at=completed_at,
        )
        session.add(slot_review)
        await session.flush()
        await session.refresh(slot_review)
        return slot_review

    await session.execute(
        update(SlotReview)
        .where(SlotReview.id == existing.id)
        .values(
            field_values=field_values,
            notes=notes,
            status=status,
            completed_at=completed_at,
            observer_trainee_id=observer_trainee_id,
        )
    )
    refreshed = await slot_review_for(session, org_id, slot_id, submitted_by)
    return refreshed  # type: ignore[return-value]


async def gp_lead_review(session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID) -> GpLeadReview | None:
    """The GP-lead review for this slot, or None if none has been started."""
    stmt = select(GpLeadReview).where(GpLeadReview.org_id == org_id, GpLeadReview.slot_id == slot_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def gp_lead_reviews_for_slots(
    session: AsyncSession, org_id: uuid.UUID, slot_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, GpLeadReview]:
    """The GP-lead review of each of these slots that has one, in one query."""
    if not slot_ids:
        return {}
    stmt = select(GpLeadReview).where(GpLeadReview.org_id == org_id, GpLeadReview.slot_id.in_(list(slot_ids)))
    return {review.slot_id: review for review in (await session.execute(stmt)).scalars()}


async def save_gp_lead_review(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    slot_id: uuid.UUID,
    revision: int,
    field_values: dict[str, Any],
    notes: str | None,
    overall_rag: str | None,
    status: str,
    reviewed_by: uuid.UUID,
    completed_at: datetime | None,
) -> GpLeadReview:
    """Create the GP-lead review for this slot, or update it if one already exists."""
    existing = await gp_lead_review(session, org_id, slot_id)
    if existing is None:
        review = GpLeadReview(
            org_id=org_id,
            slot_id=slot_id,
            revision=revision,
            field_values=field_values,
            notes=notes,
            overall_rag=overall_rag,
            status=status,
            reviewed_by=reviewed_by,
            completed_at=completed_at,
        )
        session.add(review)
        await session.flush()
        await session.refresh(review)
        return review

    await session.execute(
        update(GpLeadReview)
        .where(GpLeadReview.id == existing.id)
        .values(
            revision=revision,
            field_values=field_values,
            notes=notes,
            overall_rag=overall_rag,
            status=status,
            reviewed_by=reviewed_by,
            completed_at=completed_at,
        )
    )
    return await gp_lead_review(session, org_id, slot_id)  # type: ignore[return-value]


async def circuit_review(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID
) -> CircuitReview | None:
    """The finalised review for this circuit, or None if it has not been finalised."""
    stmt = select(CircuitReview).where(CircuitReview.org_id == org_id, CircuitReview.circuit_id == circuit_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def finalize_circuit_review(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    circuit_id: uuid.UUID,
    merged_notes: str | None,
    contributions: dict[str, Any] | None,
    finalized_by: uuid.UUID,
    at: datetime,
) -> CircuitReview:
    """Create the finalised review for this circuit, or update it if it already exists."""
    existing = await circuit_review(session, org_id, circuit_id)
    if existing is None:
        review = CircuitReview(
            org_id=org_id,
            circuit_id=circuit_id,
            merged_notes=merged_notes,
            contributions=contributions,
            finalized_by=finalized_by,
            finalized_at=at,
        )
        session.add(review)
        await session.flush()
        await session.refresh(review)
        return review

    await session.execute(
        update(CircuitReview)
        .where(CircuitReview.id == existing.id)
        .values(
            merged_notes=merged_notes,
            contributions=contributions,
            finalized_by=finalized_by,
            finalized_at=at,
        )
    )
    return await circuit_review(session, org_id, circuit_id)  # type: ignore[return-value]


async def slot_has_any_review(session: AsyncSession, slot_id: uuid.UUID) -> bool:
    """Used by `sittings` to decide whether a circuit is still editable."""
    stmt = select(SlotReview.id).where(SlotReview.slot_id == slot_id).limit(1)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def slots_with_any_review(session: AsyncSession, slot_ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
    """Which of these slots have been marked, in one query."""
    if not slot_ids:
        return set()
    stmt = select(SlotReview.slot_id).where(SlotReview.slot_id.in_(list(slot_ids))).distinct()
    return {slot_id for slot_id in (await session.execute(stmt)).scalars()}
