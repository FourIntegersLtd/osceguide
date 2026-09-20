"""The platform console's view of the voice layer. `PlatformAdmin` only."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.errors import Forbidden, error_responses
from app.core.settings import SettingsDep
from app.core.tenancy import PlatformAdmin
from app.features.voice import schemas, service_platform

router = APIRouter(tags=["voice"])


@router.get(
    "/platform/voice/capacity",
    response_model=schemas.CloudCapacityRead,
    responses=error_responses(Forbidden),
)
async def read_cloud_capacity(admin: PlatformAdmin, settings: SettingsDep) -> schemas.CloudCapacityRead:
    """How many LiveKit Cloud sessions are held against the metered cap.

    A count, not a reservation: `LiveKit Cloud "Updating"` on the dashboard is
    usually a worker recycle, and this is what says whether sessions are
    actually running through it.
    """
    _ = admin
    return await service_platform.cloud_capacity(settings)
