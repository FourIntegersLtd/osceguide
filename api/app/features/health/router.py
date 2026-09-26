from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.redis import get_redis
from app.features.health import service
from app.features.health.schemas import HealthResponse

router = APIRouter(tags=["health"])


# Public and unauthenticated: a load balancer or uptime checker calls this, not a person.
@router.get("/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
async def get_health(
    response: Response, session: Annotated[AsyncSession, Depends(get_session)]
) -> HealthResponse:
    report = await service.health_report(session, get_redis())
    if report.status == "down":
        response.status_code = 503
    return report
