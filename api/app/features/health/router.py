from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.core.db import Connection, get_connection
from app.core.redis import get_redis
from app.features.health import service
from app.features.health.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
async def get_health(
    response: Response, conn: Annotated[Connection, Depends(get_connection)]
) -> HealthResponse:
    report = await service.health_report(conn, get_redis())
    if report.status == "down":
        response.status_code = 503
    return report
