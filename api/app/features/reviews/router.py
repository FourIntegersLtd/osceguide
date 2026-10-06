"""HTTP routes for a slot's reviews: a reviewer's own review, the GP-lead
review, and a circuit's finalised review."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.ports import ClockDep
from app.core.tenancy import OrgInstitutionAdmin, OrgReader
from app.features.reviews import errors, schemas, service, service_summary

router = APIRouter(tags=["reviews"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/me/slots/{slot_id}/review",
    response_model=schemas.MySlotReviewRead | None,
    responses=error_responses(Unauthenticated, errors.SlotNotFound),
)
async def read_my_slot_review(
    slot_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> schemas.MySlotReviewRead | None:
    """A candidate's own review of one of their slots, once their result is
    released and the GP lead has completed one; null before. Never for a slot not theirs (404)."""
    return await service_summary.read_my_slot_review(session, slot_id=slot_id, user_id=principal.user_id)


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


# The caller's own review of this slot, draft or complete.
@router.get(
    "/orgs/{org_slug}/slots/{slot_id}/reviews/mine",
    response_model=schemas.SlotReviewRead | None,
    responses=error_responses(Forbidden, errors.SlotNotFound),
)
async def read_my_review(
    slot_id: uuid.UUID, workspace: OrgReader, session: Session
) -> schemas.SlotReviewRead | None:
    return await service.read_my_slot_review(
        session, workspace.org_id, slot_id, submitted_by=workspace.principal.user_id
    )


@router.put(
    "/orgs/{org_slug}/slots/{slot_id}/reviews/mine",
    response_model=schemas.SlotReviewRead,
    responses=error_responses(
        Forbidden,
        errors.SlotNotFound,
        errors.InvalidRatingError,
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


# Read the GP lead's review of one sitting slot.
@router.get(
    "/orgs/{org_slug}/slots/{slot_id}/gp-lead-review",
    response_model=schemas.GpLeadReviewRead | None,
    responses=error_responses(Forbidden),
)
async def read_gp_lead_review(
    slot_id: uuid.UUID, workspace: OrgInstitutionAdmin, session: Session
) -> schemas.GpLeadReviewRead | None:
    return await service.read_gp_lead_review(session, workspace.org_id, slot_id)


@router.put(
    "/orgs/{org_slug}/slots/{slot_id}/gp-lead-review",
    response_model=schemas.GpLeadReviewRead,
    responses=error_responses(
        Forbidden,
        errors.SlotNotFound,
        errors.ReviewConflictError,
        errors.InvalidRatingError,
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


# Whether a circuit's merged review has been finalised, and by whom. Null until it is.
@router.get(
    "/orgs/{org_slug}/circuits/{circuit_id}/review",
    response_model=schemas.CircuitReviewRead | None,
    responses=error_responses(Forbidden),
)
async def read_circuit_review(
    circuit_id: uuid.UUID, workspace: OrgReader, session: Session
) -> schemas.CircuitReviewRead | None:
    return await service.read_circuit_review(session, workspace.org_id, circuit_id)
