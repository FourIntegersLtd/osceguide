"""HTTP routes for appeals against a released result, and for deleting a candidate's data."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.auth import CurrentPrincipal
from app.core.db import SessionDep as Session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.ports import ClockDep
from app.core.tenancy import OrgInstitutionAdmin
from app.features.results import errors, schemas, service_appeals, service_candidate_erasure

router = APIRouter(tags=["results"])

_DECIDING = (
    Forbidden,
    errors.AppealNotFound,
    errors.AppealClosed,
)


# The candidate asks for their released result to be looked at again, with a reason.
@router.post(
    "/me/results/{sitting_id}/appeal",
    response_model=schemas.CandidateAppealRead,
    status_code=201,
    responses=error_responses(Unauthenticated, errors.NotReleased, errors.AppealAlreadyOpen),
)
async def request_my_appeal(
    sitting_id: uuid.UUID, body: schemas.RequestAppeal, principal: CurrentPrincipal, session: Session
) -> schemas.CandidateAppealRead:
    return await service_appeals.request_as_candidate(
        session, sitting_id=sitting_id, principal=principal, reason=body.reason
    )


@router.get(
    "/me/results/{sitting_id}/appeal",
    response_model=schemas.CandidateAppealRead | None,
    responses=error_responses(Unauthenticated),
)
async def read_my_appeal(
    sitting_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> schemas.CandidateAppealRead | None:
    """The newest review this candidate asked for on the sitting. Null if they never asked."""
    return await service_appeals.my_appeal(session, sitting_id=sitting_id, user_id=principal.user_id)


# Staff record a request the candidate made to them.
@router.post(
    "/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/appeals",
    response_model=schemas.AppealRead,
    status_code=201,
    responses=error_responses(
        Forbidden, errors.NotReleased, errors.AppealAlreadyOpen, errors.TraineeNotFound
    ),
)
async def request_appeal_for_candidate(
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
    body: schemas.RequestAppeal,
    workspace: OrgInstitutionAdmin,
    session: Session,
) -> schemas.AppealRead:
    return await service_appeals.request_for_candidate(
        session,
        workspace.org_id,
        sitting_id=sitting_id,
        trainee_id=trainee_id,
        reason=body.reason,
        actor=workspace.principal,
    )


# The organisation's appeals queue: waiting ones (default) or decided ones.
@router.get(
    "/orgs/{org_slug}/appeals",
    response_model=schemas.AppealPage,
    responses=error_responses(Forbidden),
)
async def list_appeals(
    workspace: OrgInstitutionAdmin,
    session: Session,
    decided: Annotated[bool, Query(description="Decided appeals instead of waiting ones.")] = False,
) -> schemas.AppealPage:
    return await service_appeals.queue(session, workspace.org_id, live=not decided)


# Name the second marker: an administrator who did not sign off or release the result.
@router.post(
    "/orgs/{org_slug}/appeals/{appeal_id}/assign",
    response_model=schemas.AppealRead,
    responses=error_responses(*_DECIDING, errors.SecondMarkerMustDiffer, errors.AssigneeNotAdmin),
)
async def assign_appeal(
    appeal_id: uuid.UUID,
    body: schemas.AssignAppeal,
    workspace: OrgInstitutionAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.AppealRead:
    return await service_appeals.assign(
        session, workspace.org_id, appeal_id, body, actor=workspace.principal, now=clock.now()
    )


# Turn the request down with a reason the candidate is sent.
@router.post(
    "/orgs/{org_slug}/appeals/{appeal_id}/decline",
    response_model=schemas.AppealRead,
    responses=error_responses(*_DECIDING),
)
async def decline_appeal(
    appeal_id: uuid.UUID,
    body: schemas.DeclineAppeal,
    workspace: OrgInstitutionAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.AppealRead:
    return await service_appeals.decline(
        session, workspace.org_id, appeal_id, body, actor=workspace.principal, now=clock.now()
    )


# The second marker's outcome, appended as a new released revision. Only the assigned marker.
@router.post(
    "/orgs/{org_slug}/appeals/{appeal_id}/resolve",
    response_model=schemas.AppealRead,
    responses=error_responses(
        *_DECIDING,
        errors.AppealNotAssigned,
        errors.NotAssignedMarker,
        errors.AppealStale,
        errors.IncompatibleOutcomesError,
        errors.HireReasonRequiredError,
        errors.DecisionRevisedError,
    ),
)
async def resolve_appeal(
    appeal_id: uuid.UUID,
    body: schemas.ResolveAppeal,
    workspace: OrgInstitutionAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.AppealRead:
    return await service_appeals.resolve(
        session, workspace.org_id, appeal_id, body, actor=workspace.principal, now=clock.now()
    )


# Irreversible: removes the candidate's transcripts, name, address and notes; keeps marks and results.
@router.post(
    "/orgs/{org_slug}/candidates/{trainee_id}/erase-data",
    response_model=schemas.CandidateDataDeleted,
    responses=error_responses(
        Forbidden, errors.TraineeNotFound, errors.ConfirmationMismatch, errors.AppealOpenForCandidate
    ),
)
async def erase_candidate_data(
    trainee_id: uuid.UUID,
    body: schemas.DeleteCandidateData,
    workspace: OrgInstitutionAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.CandidateDataDeleted:
    return await service_candidate_erasure.erase_candidate_data(
        session,
        workspace.org_id,
        trainee_id,
        confirmation=body.confirmation,
        actor=workspace.principal,
        now=clock.now(),
    )
