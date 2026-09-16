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
from app.features.sittings import errors, schemas, service

router = APIRouter(tags=["sittings"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/orgs/{org_slug}/sittings",
    response_model=Page[schemas.SittingRead],
    responses=error_responses(Forbidden),
)
async def list_sittings(
    workspace: OrgReader, session: Session, page: Annotated[CursorParams, Depends()]
) -> Page[schemas.SittingRead]:
    items, next_cursor = await service.list_sittings(
        session, workspace.org_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=items, next_cursor=next_cursor)


@router.post(
    "/orgs/{org_slug}/sittings",
    response_model=schemas.SittingRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.TemplateNotPublished),
)
async def create_sitting(
    body: schemas.CreateSitting, workspace: OrgAdmin, session: Session
) -> schemas.SittingRead:
    return await service.create_sitting(
        session,
        workspace.org_id,
        name=body.name,
        feedback_template_version_id=body.feedback_template_version_id,
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
    """Circuits and slots embedded, because every screen that opens a sitting
    needs all three and would otherwise fetch them one by one."""
    return await service.read_sitting(session, workspace.org_id, sitting_id)


@router.post(
    "/orgs/{org_slug}/sittings/{sitting_id}/circuits",
    response_model=schemas.CircuitRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.SittingNotFound, errors.InvalidCircuitError),
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


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/start",
    response_model=schemas.CircuitRead,
    responses=error_responses(Forbidden, errors.CircuitNotFound, errors.CircuitAlreadyEndedError),
)
async def start_circuit(
    circuit_id: uuid.UUID, workspace: OrgReader, session: Session, clock: ClockDep
) -> schemas.CircuitRead:
    """A supervisor runs the circuit they were assigned, so org membership is
    the gate rather than admin rights."""
    return await service.start_circuit(session, workspace.org_id, circuit_id, now=clock.now())


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/switch-turn",
    response_model=schemas.CircuitRead,
    responses=error_responses(
        Forbidden, errors.CircuitNotFound, errors.SlotNotFound, errors.NotPermittedInModeError
    ),
)
async def switch_turn(
    circuit_id: uuid.UUID, body: schemas.SwitchTurn, workspace: OrgReader, session: Session
) -> schemas.CircuitRead:
    return await service.switch_turn(session, workspace.org_id, circuit_id, slot_id=body.slot_id)


@router.post(
    "/orgs/{org_slug}/circuits/{circuit_id}/end",
    response_model=schemas.CircuitRead,
    responses=error_responses(Forbidden, errors.CircuitNotFound),
)
async def end_circuit(
    circuit_id: uuid.UUID, workspace: OrgReader, session: Session, clock: ClockDep
) -> schemas.CircuitRead:
    return await service.end_circuit(session, workspace.org_id, circuit_id, now=clock.now())
