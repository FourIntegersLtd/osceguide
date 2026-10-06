"""Routes that change what an organisation has already said about its people:
correcting a trainee, and renaming or removing groups and cohorts.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.ports import ClockDep
from app.core.rate_limit import OUTBOUND_EMAIL, TooManyRequests, per_user
from app.core.tenancy import OrgAdmin
from app.features.roster import errors, schemas, service_bulk, service_edit, service_groups

router = APIRouter(tags=["roster"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.patch(
    "/orgs/{org_slug}/trainees/{trainee_id}",
    response_model=schemas.TraineeRead,
    responses=error_responses(Forbidden, errors.TraineeNotFound, errors.CohortNotFound),
)
async def edit_trainee(
    trainee_id: uuid.UUID, body: schemas.UpdateTrainee, workspace: OrgAdmin, session: Session
) -> schemas.TraineeRead:
    """Only what was sent is written, so a screen that corrects a spelling does
    not clear the intake beside it."""
    return await service_edit.update_trainee(
        session,
        workspace.org_id,
        trainee_id,
        body=body,
        fields_sent=set(body.model_fields_set),
    )


@router.delete(
    "/orgs/{org_slug}/trainees/{trainee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Forbidden, errors.TraineeNotFound, errors.TraineeInUse),
)
async def delete_trainee(
    trainee_id: uuid.UUID, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> None:
    """Remove a roster row nothing was ever decided about. Returns 409
    `trainee_in_use` if a decision exists; revoke access instead in that case.
    """
    await service_edit.delete_trainee(session, workspace.org_id, trainee_id, now=clock.now())


@router.post(
    "/orgs/{org_slug}/trainees/{trainee_id}/anonymise",
    response_model=schemas.TraineeRead,
    responses=error_responses(Forbidden, errors.TraineeNotFound),
)
async def anonymise_trainee(
    trainee_id: uuid.UUID, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.TraineeRead:
    """GDPR erasure for a trainee `delete` refuses: history stays, the person's
    name and address do not.
    """
    return await service_edit.anonymise_trainee(
        session, workspace.org_id, trainee_id, actor=workspace.principal, now=clock.now()
    )


# The three routes below must stay registered before `{trainee_id}/resend-invitation`:
# FastAPI matches path segments in registration order, so a `{trainee_id}` route
# registered first would swallow "bulk" as the id and 422 on the UUID parse.
@router.post(
    "/orgs/{org_slug}/trainees/bulk/revoke",
    response_model=schemas.BulkTraineeAccessResponse,
    responses=error_responses(Forbidden),
)
async def bulk_revoke_trainees(
    body: schemas.BulkTraineeIds, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.BulkTraineeAccessResponse:
    """Revoke access for a selection from the roster table at once. Each row goes
    through the same `POST /trainees/{id}/access` decision; an id from another
    organisation, or repeated in the request, is reported rather than acted on twice.
    """
    results = await service_bulk.bulk_revoke_trainees(
        session, workspace.org_id, body.trainee_ids, now=clock.now()
    )
    return schemas.BulkTraineeAccessResponse(results=results)


@router.post(
    "/orgs/{org_slug}/trainees/bulk/cohort",
    response_model=schemas.BulkTraineeCohortResponse,
    responses=error_responses(Forbidden, errors.CohortNotFound),
)
async def bulk_set_trainee_cohort(
    body: schemas.BulkSetTraineeCohort, workspace: OrgAdmin, session: Session
) -> schemas.BulkTraineeCohortResponse:
    """Move a selection into one intake, or clear it, at once. Returns 404
    `cohort_not_found` for the whole request if `cohort_id` does not name an
    intake of this organisation; each trainee id is otherwise reported on its own.
    """
    results = await service_bulk.bulk_set_trainee_cohort(
        session, workspace.org_id, body.trainee_ids, cohort_id=body.cohort_id
    )
    return schemas.BulkTraineeCohortResponse(results=results)


@router.post(
    "/orgs/{org_slug}/trainees/bulk/resend-invitation",
    response_model=schemas.BulkTraineeInvitationResponse,
    responses=error_responses(Forbidden),
)
async def bulk_resend_trainee_invitations(
    body: schemas.BulkTraineeIds, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.BulkTraineeInvitationResponse:
    """Resend the sign-in invitation to a selection at once, each row through the
    same `POST /trainees/{id}/resend-invitation` decision.
    """
    results = await service_bulk.bulk_resend_trainee_invitations(
        session, workspace.org_id, body.trainee_ids, now=clock.now()
    )
    return schemas.BulkTraineeInvitationResponse(results=results)


@router.post(
    "/orgs/{org_slug}/trainees/{trainee_id}/resend-invitation",
    response_model=schemas.InvitationRead,
    responses=error_responses(
        TooManyRequests, Forbidden, errors.TraineeNotFound, errors.InvitationNotPending
    ),
    dependencies=[Depends(per_user(OUTBOUND_EMAIL))],
)
async def resend_invitation(
    trainee_id: uuid.UUID, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.InvitationRead:
    """Send the choose-a-password link again, as a new token. Returns 409
    `invitation_not_pending` if the person has already chosen a password.
    """
    return await service_edit.resend_invitation(session, workspace.org_id, trainee_id, now=clock.now())


@router.patch(
    "/orgs/{org_slug}/trainee-groups/{group_id}",
    response_model=schemas.GroupRead,
    responses=error_responses(Forbidden, errors.GroupNotFound, errors.GroupExists),
)
async def rename_group(
    group_id: uuid.UUID, body: schemas.UpdateGroup, workspace: OrgAdmin, session: Session
) -> schemas.GroupRead:
    """Rename a group. Its members are unaffected."""
    return await service_groups.rename_group(session, workspace.org_id, group_id, label=body.label)


@router.delete(
    "/orgs/{org_slug}/trainee-groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Forbidden, errors.GroupNotFound, errors.GroupNotEmpty),
)
async def remove_group(group_id: uuid.UUID, workspace: OrgAdmin, session: Session) -> None:
    """Refused while anybody is still in it: the membership, and anything
    addressed to the group, goes with it, so the emptied list is stated first."""
    await service_groups.delete_group(session, workspace.org_id, group_id)


# Renames a cohort, or changes its academic year.
@router.patch(
    "/orgs/{org_slug}/cohorts/{cohort_id}",
    response_model=schemas.CohortRead,
    responses=error_responses(Forbidden, errors.CohortNotFound, errors.CohortExists),
)
async def edit_cohort(
    cohort_id: uuid.UUID, body: schemas.UpdateCohort, workspace: OrgAdmin, session: Session
) -> schemas.CohortRead:
    return await service_groups.update_cohort(
        session,
        workspace.org_id,
        cohort_id,
        body=body,
        fields_sent=set(body.model_fields_set),
    )


@router.delete(
    "/orgs/{org_slug}/cohorts/{cohort_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Forbidden, errors.CohortNotFound, errors.CohortInUse),
)
async def remove_cohort(cohort_id: uuid.UUID, workspace: OrgAdmin, session: Session) -> None:
    """Refused while trainees still belong to it — a silent `SET NULL` would
    read as those people having never had an intake."""
    await service_groups.delete_cohort(session, workspace.org_id, cohort_id)
