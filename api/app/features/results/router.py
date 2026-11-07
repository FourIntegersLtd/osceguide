"""HTTP routes for recording, signing off and releasing a candidate's decision,
plus the candidate's own routes for reading and acknowledging it."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from fastapi.responses import Response

from app.core.auth import CurrentPrincipal
from app.core.db import SessionDep as Session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.ports import ClockDep
from app.core.tenancy import OrgInstitutionAdmin
from app.features.results import errors, schemas, service, service_candidate, service_result_pdf

router = APIRouter(tags=["results"])


# Read the result decision for one candidate in a sitting.
@router.get(
    "/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/decision",
    response_model=schemas.DecisionRead | None,
    responses=error_responses(Forbidden),
)
async def read_decision(
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
    workspace: OrgInstitutionAdmin,
    session: Session,
) -> schemas.DecisionRead | None:
    """Null until somebody records one: no decision yet is an ordinary state, not an error."""
    return await service.read_decision(session, workspace.org_id, sitting_id, trainee_id)


@router.put(
    "/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/decision",
    response_model=schemas.DecisionRead,
    responses=error_responses(
        Forbidden,
        errors.TraineeNotFound,
        errors.SittingNotFound,
        errors.IncompatibleOutcomesError,
        errors.RecruitmentOutsideExamError,
        errors.HireReasonRequiredError,
        errors.DecisionOutsideExamError,
        errors.CandidateDidNotSitError,
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
        expected_revision=body.expected_revision,
        actor_id=workspace.principal.user_id,
    )


# Put a name to the current draft decision. Refused if it has no outcome or rationale yet.
@router.post(
    "/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/decision/sign-off",
    response_model=schemas.DecisionRead,
    responses=error_responses(
        Forbidden,
        errors.ResultNotFound,
        errors.NotSignableError,
        errors.HireReasonRequiredError,
        errors.InvalidWorkflowError,
        errors.EvidenceChangedError,
        errors.ReviewsPendingError,
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


# Release several signed-off candidates at once; each still gets their own email.
@router.post(
    "/orgs/{org_slug}/sittings/{sitting_id}/decisions/release",
    response_model=schemas.BulkReleaseResult,
    responses=error_responses(Forbidden),
)
async def release_many(
    sitting_id: uuid.UUID,
    body: schemas.BulkRelease,
    workspace: OrgInstitutionAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.BulkReleaseResult:
    return await service.release_many(
        session,
        workspace.org_id,
        sitting_id=sitting_id,
        candidates=body.candidates,
        actor_id=workspace.principal.user_id,
        now=clock.now(),
    )


@router.post(
    "/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/decision/release",
    response_model=schemas.DecisionRead,
    responses=error_responses(
        Forbidden,
        errors.ResultNotFound,
        errors.EvidenceChangedError,
        errors.InvalidWorkflowError,
        errors.NotReleasableError,
    ),
)
async def release(
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
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
        actor_id=workspace.principal.user_id,
        now=clock.now(),
    )


# The released result as a PDF. A draft is refused; the file matches what the candidate can download.
@router.get(
    "/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/result.pdf",
    response_class=Response,
    responses={
        **error_responses(Forbidden, errors.SittingNotFound, errors.TraineeNotFound, errors.NotReleased),
        200: {
            "description": "The candidate's released result as a PDF.",
            "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
        },
    },
)
async def read_result_pdf(
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
    workspace: OrgInstitutionAdmin,
    session: Session,
    clock: ClockDep,
) -> Response:
    payload, filename = await service_result_pdf.render_admin_result_pdf(
        session,
        org_id=workspace.org_id,
        sitting_id=sitting_id,
        trainee_id=trainee_id,
        actor=workspace.principal,
        generated_at=clock.now(),
    )
    return _pdf_attachment(payload, filename)


# What the candidate would see, readable before release. Never carries moderation notes.
@router.get(
    "/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/result-preview",
    response_model=schemas.TraineeResultRead,
    responses=error_responses(
        Forbidden, errors.SittingNotFound, errors.TraineeNotFound, errors.ResultNotFound
    ),
)
async def read_result_preview(
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
    workspace: OrgInstitutionAdmin,
    session: Session,
) -> schemas.TraineeResultRead:
    return await service_candidate.preview_result(session, workspace.org_id, sitting_id, trainee_id)


# Registered before `/me/results/{sitting_id}`: that pattern would otherwise take `….pdf`
# as the id and refuse it as an invalid UUID.
@router.get(
    "/me/results/{sitting_id}.pdf",
    response_class=Response,
    responses={
        **error_responses(Unauthenticated, errors.NotReleased),
        200: {
            "description": "This candidate's released result as a PDF.",
            "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
        },
    },
)
async def read_my_result_pdf(
    sitting_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: Session,
    clock: ClockDep,
) -> Response:
    payload, filename = await service_result_pdf.render_my_result_pdf(
        session,
        sitting_id=sitting_id,
        user_id=principal.user_id,
        generated_at=clock.now(),
    )
    return _pdf_attachment(payload, filename)


@router.get(
    "/me/results/{sitting_id}",
    response_model=schemas.TraineeResultRead | None,
    responses=error_responses(Unauthenticated),
)
async def read_my_result(
    sitting_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> schemas.TraineeResultRead | None:
    """Released revisions only, and narrower than the internal record. Null until one is released."""
    return await service_candidate.read_my_result(session, sitting_id, principal.user_id)


def _pdf_attachment(payload: bytes, filename: str) -> Response:
    """A PDF the browser saves under `filename` rather than displaying inline."""
    return Response(
        content=payload,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
