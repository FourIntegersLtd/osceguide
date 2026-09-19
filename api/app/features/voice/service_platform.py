"""The voice layer as the platform console reads it."""

from __future__ import annotations

from app.core.settings import Settings
from app.features.voice import capacity
from app.features.voice.schemas import CloudCapacityRead


async def cloud_capacity(settings: Settings) -> CloudCapacityRead:
    """The Cloud slot count as the console reads it. Looks; never reserves."""
    active = await capacity.active_slots()
    return CloudCapacityRead(
        overflow_enabled=settings.livekit_cloud_overflow_enabled,
        max_concurrent=settings.livekit_cloud_max_concurrent,
        active=active,
        free=None if active is None else max(0, settings.livekit_cloud_max_concurrent - active),
    )
