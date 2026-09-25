"""The platform console's view of the voice layer. `PlatformAdmin` only."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.errors import Forbidden, error_responses
from app.core.settings import SettingsDep
from app.core.tenancy import PlatformAdmin
from app.features.voice import schemas, service

router = APIRouter(tags=["voice"])


@router.get(
    "/platform/voice/capacity",
    response_model=schemas.CloudCapacityRead,
    responses=error_responses(Forbidden),
)
async def read_cloud_capacity(admin: PlatformAdmin, settings: SettingsDep) -> schemas.CloudCapacityRead:
    """How many LiveKit Cloud sessions are currently held against the metered cap."""
    _ = admin
    return await service.cloud_capacity(settings)
