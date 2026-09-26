from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.ports import ClockDep
from app.core.tenancy import OrgInstitutionAdmin
from app.features.results import errors, schemas, service, service_candidate

router = APIRouter(tags=["results"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/decision",
    response_model=schemas.DecisionRead,
    responses=error_responses(Forbidden, errors.ResultNotFound),
)
async def read_decision(
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
    workspace: OrgInstitutionAdmin,
    session: Session,
) -> schemas.DecisionRead:
    return await service.read_decision(session, workspace.org_id, sitting_id, trainee_id)


@router.put(
    "/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/decision",
    response_model=schemas.DecisionRead,
    responses=error_responses(
        Forbidden,
        errors.TraineeNotFound,
        errors.IncompatibleOutcomesError,
        errors.InvalidWorkflowError,
        errors.DecisionRevisedError,
    ),
)
async def save_decision(
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
    body: schemas.SaveDecision,
    workspace: OrgInstitutionAdmin,
    session: Session,
) -> schemas.DecisionRead:
    """Save a decision as a draft. Each save is a new revision.

    `expected_revision` names the revision this screen read; a save against a
    stale one is refused with `decision_revised` rather than superseding it.
    """
    return await service.save_draft(
        session,
        workspace.org_id,
        sitting_id=sitting_id,
        trainee_id=trainee_id,
        assessment_outcome=body.assessment_outcome,
        recruitment_outcome=body.recruitment_outcome,
        rationale=body.rationale,
        moderation_notes=body.moderation_notes,
        evidence=body.evidence,
        expected_revision=body.expected_revision,
        actor_id=workspace.principal.user_id,
    )


# Put a name to the current draft decision. Refused if it has no outcome or rationale yet.
@router.post(
    "/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/decision/sign-off",
    response_model=schemas.DecisionRead,
    responses=error_responses(
        Forbidden, errors.ResultNotFound, errors.NotSignableError, errors.InvalidWorkflowError
    ),
)
async def sign_off(
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
    workspace: OrgInstitutionAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.DecisionRead:
    return await service.sign_off(
        session,
        workspace.org_id,
        sitting_id=sitting_id,
        trainee_id=trainee_id,
        actor_id=workspace.principal.user_id,
        now=clock.now(),
    )


@router.post(
    "/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/decision/release",
    response_model=schemas.DecisionRead,
    responses=error_responses(
        Forbidden, errors.ResultNotFound, errors.EvidenceChangedError, errors.InvalidWorkflowError
    ),
)
async def release(
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
    body: schemas.SaveDecision,
    workspace: OrgInstitutionAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.DecisionRead:
    """Release re-checks the evidence: a station re-marked between sign-off and
    release would otherwise send a candidate an outcome nobody approved."""
    return await service.release(
        session,
        workspace.org_id,
        sitting_id=sitting_id,
        trainee_id=trainee_id,
        current_evidence=body.evidence,
        actor_id=workspace.principal.user_id,
        now=clock.now(),
    )


@router.get(
    "/me/results/{sitting_id}",
    response_model=schemas.TraineeResultRead,
    responses=error_responses(Unauthenticated, errors.NotReleased),
)
async def read_my_result(
    sitting_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> schemas.TraineeResultRead:
    """Released revisions only, and narrower than the internal record."""
    return await service_candidate.read_my_result(session, sitting_id, principal.user_id)


@router.post(
    "/me/results/{sitting_id}/acknowledge",
    response_model=schemas.ResultAcknowledgement,
    responses=error_responses(Unauthenticated, errors.NotReleased),
)
async def acknowledge_my_result(
    sitting_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> schemas.ResultAcknowledgement:
    """Record that the candidate has read their result. Idempotent per revision."""
    return await service_candidate.acknowledge_my_result(session, sitting_id, principal.user_id)
