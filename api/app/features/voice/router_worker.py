"""The cloud-slot routes the LiveKit workers call.

Part of the worker contract: `voice_infra.cloud_slot` extends the slot when a
session starts and releases it on shutdown. A backend that does not serve these
leaks a Cloud slot per session until the expiry score reclaims it.

Both are best effort on the worker's side, so both answer 200 with what
happened rather than refusing — failing the call would end a live session over
an accounting detail.
"""

from __future__ import annotations

import contextlib
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import require_worker_secret
from app.core.errors import Unauthenticated, error_responses
from app.core.events import get_event_bus, voice_queue_topic
from app.core.ports import EventBus
from app.core.settings import SettingsDep
from app.features.voice import capacity, schemas, seats

router = APIRouter(
    tags=["worker"],
    dependencies=[Depends(require_worker_secret)],
)


@router.post(
    "/livekit-cloud-slot/extend",
    response_model=schemas.CloudSlotResult,
    responses=error_responses(Unauthenticated),
)
async def extend_cloud_slot(body: schemas.CloudSlotPost, settings: SettingsDep) -> schemas.CloudSlotResult:
    """A worker has connected, so hold the room's seat for a whole session.

    Every worker calls this, on Cloud or ours, so it lengthens whichever seat
    the room holds. Only ever one that exists: a room nobody reserved must not
    start being counted against either.
    """
    on_cloud = await capacity.extend(settings, body.room_name)
    on_ours = await seats.extend(settings, body.room_name)
    return schemas.CloudSlotResult(room_name=body.room_name, changed=on_cloud or on_ours)


@router.post(
    "/livekit-cloud-slot/release",
    response_model=schemas.CloudSlotResult,
    responses=error_responses(Unauthenticated),
)
async def release_cloud_slot(
    body: schemas.CloudSlotPost,
    settings: SettingsDep,
    bus: Annotated[EventBus, Depends(get_event_bus)],
) -> schemas.CloudSlotResult:
    """The session is over. Give the seat back before its expiry would, and tell the line."""
    on_cloud = await capacity.release(settings, body.room_name)
    on_ours = await seats.release(body.room_name)
    if on_cloud or on_ours:
        # Best effort, like the release itself: a waiter who misses this still
        # re-reads their place on the stream's next heartbeat.
        with contextlib.suppress(Exception):
            await bus.publish(voice_queue_topic(), "seat_freed")
    return schemas.CloudSlotResult(room_name=body.room_name, changed=on_cloud or on_ours)
