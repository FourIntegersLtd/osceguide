"""Read-only catalog of station autogenerate profiles."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.auth import CurrentPrincipal
from app.core.errors import Unauthenticated, error_responses
from app.features.stations import errors, service_generation_profiles

router = APIRouter(tags=["station-generation-profiles"])


@router.get(
    "/station-generation-profiles",
    responses=error_responses(Unauthenticated),
)
async def list_station_generation_profiles(_principal: CurrentPrincipal) -> dict[str, Any]:
    return {"items": service_generation_profiles.list_profiles()}


@router.get(
    "/station-generation-profiles/{profile_key}",
    responses=error_responses(Unauthenticated, errors.GenerationProfileNotFound),
)
async def get_station_generation_profile(profile_key: str, _principal: CurrentPrincipal) -> dict[str, Any]:
    return service_generation_profiles.profile_detail(profile_key)
