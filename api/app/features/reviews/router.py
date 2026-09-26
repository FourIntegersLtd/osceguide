"""HTTP routes for a slot's reviews: a reviewer's own review, the GP-lead
review, and a circuit's finalised review."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.ports import ClockDep
from app.core.tenancy import OrgInstitutionAdmin, OrgReader
from app.features.reviews import errors, schemas, service, service_summary

router = APIRouter(tags=["reviews"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/orgs/{org_slug}/slots/{slot_id}/reviews",
    response_model=schemas.SlotReviewsRead,
    responses=error_responses(Forbidden),
)
async def list_slot_reviews(
    slot_id: uuid.UUID, workspace: OrgReader, session: Session
) -> schemas.SlotReviewsRead:
    """Every review of this slot, with what they add up to.

    Not paginated: a slot has as many reviews as it has observers.
    """
    return await service_summary.read_slot_reviews(session, workspace.org_id, slot_id)


@router.put(
    "/orgs/{org_slug}/slots/{slot_id}/reviews/mine",
    response_model=schemas.SlotReviewRead,
    responses=error_responses(
        Forbidden,
        errors.SlotNotFound,
        errors.InvalidRagError,
        errors.ReviewIncompleteError,
        errors.NothingToReviewError,
    ),
)
async def submit_my_review(
    slot_id: uuid.UUID,
    body: schemas.SubmitSlotReview,
    workspace: OrgReader,
    session: Session,
    clock: ClockDep,
) -> schemas.SlotReviewRead:
    """Submit or update your own review of this slot. One per reviewer per slot."""
    return await service.submit_slot_review(
        session,
        workspace.org_id,
        slot_id,
        submitted_by=workspace.principal.user_id,
        field_values=body.field_values,
        notes=body.notes,
        status=body.status,
        observer_trainee_id=body.observer_trainee_id,
        now=clock.now(),
    )


@router.get(
    "/orgs/{org_slug}/slots/{slot_id}/gp-lead-review",
    response_model=schemas.GpLeadReviewRead,
    responses=error_responses(Forbidden, errors.ReviewNotFound),
)
async def read_gp_lead_review(
    slot_id: uuid.UUID, workspace: OrgInstitutionAdmin, session: Session
) -> schemas.GpLeadReviewRead:
    return await service.read_gp_lead_review(session, workspace.org_id, slot_id)


@router.put(
    "/orgs/{org_slug}/slots/{slot_id}/gp-lead-review",
    response_model=schemas.GpLeadReviewRead,
    responses=error_responses(
        Forbidden,
        errors.SlotNotFound,
        errors.ReviewConflictError,
        errors.InvalidRagError,
        errors.ReviewIncompleteError,
        errors.NothingToReviewError,
    ),
)
async def save_gp_lead_review(
    slot_id: uuid.UUID,
    body: schemas.SaveGpLeadReview,
    workspace: OrgInstitutionAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.GpLeadReviewRead:
    """Save the GP-lead review for this slot. Requires the last-read `revision`
    to prevent two reviewers overwriting one another."""
    return await service.save_gp_lead_review(
        session,
        workspace.org_id,
        slot_id,
        presented_revision=body.revision,
        field_values=body.field_values,
        notes=body.notes,
        overall_rag=body.overall_rag,
        status=body.status,
        reviewed_by=workspace.principal.user_id,
        now=clock.now(),
    )


# Finalise a supervisor's merged review for a whole circuit.
@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/review/finalize",
    response_model=schemas.CircuitReviewRead,
    responses=error_responses(Forbidden),
)
async def finalize_circuit_review(
    circuit_id: uuid.UUID,
    body: schemas.FinalizeCircuitReview,
    workspace: OrgReader,
    session: Session,
    clock: ClockDep,
) -> schemas.CircuitReviewRead:
    return await service.finalize_circuit(
        session,
        workspace.org_id,
        circuit_id,
        merged_notes=body.merged_notes,
        finalized_by=workspace.principal.user_id,
        now=clock.now(),
    )
