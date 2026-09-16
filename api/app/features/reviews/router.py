from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import Page
from app.core.ports import ClockDep
from app.core.tenancy import OrgInstitutionAdmin, OrgReader
from app.features.reviews import errors, schemas, service

router = APIRouter(tags=["reviews"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/orgs/{org_slug}/slots/{slot_id}/reviews",
    response_model=Page[schemas.SlotReviewRead],
    responses=error_responses(Forbidden),
)
async def list_slot_reviews(
    slot_id: uuid.UUID, workspace: OrgReader, session: Session
) -> Page[schemas.SlotReviewRead]:
    items = await service.read_slot_reviews(session, workspace.org_id, slot_id)
    return Page(items=items, next_cursor=None)


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
    """One review per person per slot, edited in place.

    `mine` rather than an id: a reviewer has exactly one, and addressing it by
    id would invite editing somebody else's.
    """
    return await service.submit_slot_review(
        session,
        workspace.org_id,
        slot_id,
        submitted_by=workspace.principal.user_id,
        field_values=body.field_values,
        notes=body.notes,
        status=body.status,
        observer_trainee_id=body.observer_trainee_id,
        # Wired to the bound feedback template once templates carry their
        # domain list; until then a draft is always completable.
        required_domains=set(),
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
    ),
)
async def save_gp_lead_review(
    slot_id: uuid.UUID,
    body: schemas.SaveGpLeadReview,
    workspace: OrgInstitutionAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.GpLeadReviewRead:
    """Institution admin only, and revisioned.

    The revision the client last read is required, so two people with the same
    screen open cannot silently overwrite one another.
    """
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
        required_domains=set(),
        now=clock.now(),
    )


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
