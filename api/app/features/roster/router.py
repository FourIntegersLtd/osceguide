"""Routes for an organisation's roster: listing and adding trainees, setting
their access, and the cohorts and groups they can be sorted into.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.tenancy import OrgAdmin, OrgReader
from app.features.roster import errors, router_admin, schemas, service, service_groups

router = APIRouter(tags=["roster"])
# Routes that change an existing entry live in `router_admin.py`; mounted here so
# `main.py` only needs to import this one router.
router.include_router(router_admin.router)

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/orgs/{org_slug}/trainees",
    response_model=Page[schemas.TraineeRead],
    responses=error_responses(Forbidden),
)
async def list_trainees(
    workspace: OrgReader, session: Session, page: Annotated[CursorParams, Depends()]
) -> Page[schemas.TraineeRead]:
    """Readable by any member: a supervisor needs names to run a circuit."""
    trainees, next_cursor = await service.list_trainees(
        session, workspace.org_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=trainees, next_cursor=next_cursor)


@router.post(
    "/orgs/{org_slug}/trainees",
    response_model=schemas.TraineeRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.TraineeExists),
)
async def add_trainee(
    body: schemas.CreateTrainee, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.TraineeRead:
    """An address with no account is invited and linked in the same call."""
    return await service.add_trainee(
        session,
        workspace.org_id,
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
        cohort_id=body.cohort_id,
        now=clock.now(),
    )


@router.post(
    "/orgs/{org_slug}/trainees/bulk",
    response_model=schemas.BulkTraineesResult,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden),
)
async def add_trainees(
    body: schemas.BulkCreateTrainees, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.BulkTraineesResult:
    """A spreadsheet's worth of trainees. Duplicates are reported, not fatal."""
    return await service.add_trainees(session, workspace.org_id, entries=body.trainees, now=clock.now())


@router.post(
    "/orgs/{org_slug}/trainees/{trainee_id}/access",
    response_model=schemas.TraineeRead,
    responses=error_responses(Forbidden, errors.TraineeNotFound),
)
async def set_access(
    trainee_id: uuid.UUID,
    body: schemas.TraineeAccess,
    workspace: OrgAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.TraineeRead:
    """One route for revoke and restore: they are the same decision, and two
    routes invite one of them to be forgotten."""
    return await service.set_access(
        session, workspace.org_id, trainee_id, revoked=body.revoked, now=clock.now()
    )


@router.get(
    "/orgs/{org_slug}/cohorts",
    response_model=Page[schemas.CohortRead],
    responses=error_responses(Forbidden),
)
async def list_cohorts(workspace: OrgReader, session: Session) -> Page[schemas.CohortRead]:
    return Page(items=await service_groups.list_cohorts(session, workspace.org_id), next_cursor=None)


@router.post(
    "/orgs/{org_slug}/cohorts",
    response_model=schemas.CohortRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.CohortExists),
)
async def add_cohort(body: schemas.CreateCohort, workspace: OrgAdmin, session: Session) -> schemas.CohortRead:
    """An intake is named once per organisation: `(org, name)` is unique, and a
    spreadsheet that repeats one is a mistake worth naming."""
    return await service_groups.add_cohort(
        session, workspace.org_id, name=body.name, academic_year=body.academic_year
    )


@router.get(
    "/orgs/{org_slug}/trainee-groups",
    response_model=Page[schemas.GroupRead],
    responses=error_responses(Forbidden),
)
async def list_groups(workspace: OrgReader, session: Session) -> Page[schemas.GroupRead]:
    return Page(items=await service_groups.list_groups(session, workspace.org_id), next_cursor=None)


@router.post(
    "/orgs/{org_slug}/trainee-groups",
    response_model=schemas.GroupRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.GroupExists),
)
async def add_group(body: schemas.CreateGroup, workspace: OrgAdmin, session: Session) -> schemas.GroupRead:
    return await service_groups.add_group(session, workspace.org_id, label=body.label)


@router.put(
    "/orgs/{org_slug}/trainee-groups/{group_id}/members",
    response_model=schemas.GroupRead,
    responses=error_responses(Forbidden, errors.GroupNotFound, errors.TraineeNotFound),
)
async def set_group_members(
    group_id: uuid.UUID,
    body: schemas.SetGroupMembers,
    workspace: OrgAdmin,
    session: Session,
) -> schemas.GroupRead:
    """Replace the group's full membership list."""
    return await service_groups.set_group_members(
        session, workspace.org_id, group_id, trainee_ids=body.trainee_ids
    )


# Who is in a trainee group, a page at a time.
@router.get(
    "/orgs/{org_slug}/trainee-groups/{group_id}/members",
    response_model=Page[schemas.TraineeRead],
    responses=error_responses(Forbidden, errors.GroupNotFound),
)
async def list_group_members(
    group_id: uuid.UUID,
    workspace: OrgReader,
    session: Session,
    page: Annotated[CursorParams, Depends()],
) -> Page[schemas.TraineeRead]:
    trainees, next_cursor = await service_groups.list_group_members(
        session, workspace.org_id, group_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=trainees, next_cursor=next_cursor)


@router.post(
    "/orgs/{org_slug}/roster/resolve",
    response_model=schemas.ResolvedRoster,
    responses=error_responses(Forbidden, errors.GroupNotFound),
)
async def resolve_roster(
    body: schemas.ResolveRosterRequest, workspace: OrgReader, session: Session
) -> schemas.ResolvedRoster:
    """Preview who a circuit would contain.

    A POST because it takes a body, not because it changes anything — the
    alternative is a query string of repeated uuids.
    """
    return await service_groups.resolve_roster(
        session,
        workspace.org_id,
        trainee_ids=body.trainee_ids,
        group_ids=body.group_ids,
    )
