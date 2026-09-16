from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.ports import ClockDep
from app.features.dashboard import schemas, service

router = APIRouter(tags=["dashboard"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/me/dashboard",
    response_model=schemas.Dashboard,
    responses=error_responses(Unauthenticated),
)
async def read_dashboard(principal: CurrentPrincipal, session: Session, clock: ClockDep) -> schemas.Dashboard:
    """One call for a screen that currently makes seven.

    A read model over several aggregates. "Dashboard" is not a domain concept —
    nothing owns one and no rule is enforced about it — which is why this slice
    has no tables and no domain module.
    """
    return await service.build(session, principal.user_id, now=clock.now())
