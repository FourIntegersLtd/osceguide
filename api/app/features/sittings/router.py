"""Scheduling a sitting and shaping the circuits inside it.

The routes here are the desk work: create a sitting, build or rebuild a
circuit, add latecomers, edit what has not started yet. Running a live
circuit is `router_run.py`; overriding one is `router_overrides.py`.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import CursorParams, Page
from app.core.tenancy import OrgAdmin, OrgReader, OrgStaff
from app.features.sittings import errors, schemas, service, service_edit, service_structure

router = APIRouter(tags=["sittings"])

Session = Annotated[AsyncSession, Depends(get_session)]


# A page of this organisation's sittings, newest first.
@router.get(
    "/orgs/{org_slug}/sittings",
    response_model=Page[schemas.SittingRead],
    responses=error_responses(Forbidden),
)
async def list_sittings(
    workspace: OrgReader, session: Session, page: Annotated[CursorParams, Depends()]
) -> Page[schemas.SittingRead]:
    sittings, next_cursor = await service.list_sittings(
        session, workspace.org_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=sittings, next_cursor=next_cursor)


# Schedule a new sitting against a programme's published rubric.
@router.post(
    "/orgs/{org_slug}/sittings",
    response_model=schemas.SittingRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        Forbidden,
        errors.ProgrammeRequired,
        errors.ProgrammeNotFound,
        errors.ExamRubricNotReady,
        errors.RubricVersionNotFound,
        errors.RubricVersionNotPublished,
    ),
)
async def create_sitting(
    body: schemas.CreateSitting, workspace: OrgAdmin, session: Session
) -> schemas.SittingRead:
    return await service.create_sitting(
        session,
        workspace.org_id,
        name=body.name,
        mode=body.mode,
        sitting_type=body.sitting_type,
        scheduled_for=body.scheduled_for,
        programme_id=body.programme_id,
    )


@router.get(
    "/orgs/{org_slug}/sittings/{sitting_id}",
    response_model=schemas.SittingRead,
    responses=error_responses(Forbidden, errors.SittingNotFound),
)
async def read_sitting(sitting_id: uuid.UUID, workspace: OrgReader, session: Session) -> schemas.SittingRead:
    """Circuits and slots are embedded, since a sitting screen needs all three."""
    return await service.read_sitting(session, workspace.org_id, sitting_id)


@router.put(
    "/orgs/{org_slug}/sittings/{sitting_id}",
    response_model=schemas.SittingRead,
    responses=error_responses(
        Forbidden,
        errors.SittingNotFound,
        errors.SittingLockedError,
        errors.InvalidCircuitError,
        errors.ProgrammeNotFound,
        errors.ExamRubricNotReady,
        errors.RubricVersionNotFound,
        errors.RubricVersionNotPublished,
    ),
)
async def update_sitting(
    sitting_id: uuid.UUID, body: schemas.UpdateSitting, workspace: OrgAdmin, session: Session
) -> schemas.SittingRead:
    """Correct a sitting that has already been scheduled.

    Only fields sent are written. The name and date stay editable indefinitely.
    The mode, type and programme freeze once any circuit has started, since
    marks already given were given against the other answer.
    """
    return await service_edit.update_sitting(session, workspace.org_id, sitting_id, body=body)


# Build a new circuit inside this sitting, from a roster and a station list.
@router.post(
    "/orgs/{org_slug}/sittings/{sitting_id}/circuits",
    response_model=schemas.CircuitRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        Forbidden,
        errors.SittingNotFound,
        errors.InvalidCircuitError,
        errors.TraineeRevokedError,
        errors.TraineeNotOnRosterError,
    ),
)
async def add_circuit(
    sitting_id: uuid.UUID, body: schemas.CreateCircuit, workspace: OrgAdmin, session: Session
) -> schemas.CircuitRead:
    return await service.add_circuit(
        session,
        workspace.org_id,
        sitting_id,
        name=body.name,
        trainee_ids=body.trainee_ids,
        station_version_ids=body.station_version_ids,
        supervisor_user_id=body.supervisor_user_id,
        timing=body.timing,
    )


@router.put(
    "/orgs/{org_slug}/circuits/{circuit_id}",
    response_model=schemas.CircuitRead,
    responses=error_responses(
        Forbidden,
        errors.CircuitNotFound,
        errors.SittingNotFound,
        errors.CircuitAlreadyEndedError,
        errors.CircuitLockedError,
        errors.InvalidCircuitError,
        errors.TraineeRevokedError,
        errors.TraineeNotOnRosterError,
    ),
)
async def rebuild_circuit(
    circuit_id: uuid.UUID, body: schemas.RebuildCircuit, workspace: OrgAdmin, session: Session
) -> schemas.CircuitRead:
    """Change who is on a circuit and which stations they sit.

    Refused with `circuit_locked` (409) if a consultation is in progress, if
    feedback has been recorded, or if any station has already been run.
    """
    return await service_structure.rebuild_circuit(
        session,
        workspace.org_id,
        circuit_id,
        trainee_ids=body.trainee_ids,
        station_version_ids=body.station_version_ids,
        name=body.name,
        supervisor_user_id=body.supervisor_user_id,
        timing=body.timing,
    )


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/append-trainees",
    response_model=schemas.CircuitRead,
    responses=error_responses(
        Forbidden,
        errors.CircuitNotFound,
        errors.CircuitAlreadyEndedError,
        errors.NotPermittedInModeError,
        errors.InvalidCircuitError,
        errors.TraineeAlreadyOnCircuitError,
        errors.StationNotOnCircuitError,
        errors.TraineeRevokedError,
        errors.TraineeNotOnRosterError,
    ),
)
async def append_trainees(
    circuit_id: uuid.UUID,
    body: schemas.AppendTrainees,
    workspace: OrgStaff,
    session: Session,
) -> schemas.CircuitRead:
    """Add people to a training circuit, into the room it is already using.

    Each arrival may name the station it takes, positionally with
    `trainee_ids`; name none and they all join the station the circuit is
    currently on. Either way, the station must already be one this circuit
    runs.
    """
    return await service_structure.append_trainees(
        session,
        workspace.org_id,
        circuit_id,
        trainee_ids=body.trainee_ids,
        station_version_ids=body.station_version_ids,
    )
