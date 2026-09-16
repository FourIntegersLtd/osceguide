"""The cloud-slot routes the LiveKit workers call.

Part of the worker contract, and the last two endpoints of it that were
missing: `voice_infra.cloud_slot` extends the slot when a session starts and
releases it on shutdown, addressing both by the paths in its
`VOICE_BACKENDS_JSON` entry. A backend that does not serve them leaks a Cloud
slot per session until the expiry score reclaims it, so the cap silently
shrinks over a busy day.

Both are best effort on the worker's side — it logs the failure and carries on
— so both answer 200 with what happened rather than refusing. There is nothing
useful a worker could do with an error here, and failing the call would end a
live session over an accounting detail.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import require_worker_secret
from app.core.errors import Unauthenticated, error_responses
from app.core.settings import SettingsDep
from app.features.voice import capacity, schemas

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
    """A worker has connected, so hold the slot for a whole session.

    Only lengthens a room that already holds one: a self-hosted session in a
    room nobody reserved must not start being counted against the Cloud cap.
    """
    return schemas.CloudSlotResult(
        room_name=body.room_name, changed=await capacity.extend(settings, body.room_name)
    )


@router.post(
    "/livekit-cloud-slot/release",
    response_model=schemas.CloudSlotResult,
    responses=error_responses(Unauthenticated),
)
async def release_cloud_slot(body: schemas.CloudSlotPost, settings: SettingsDep) -> schemas.CloudSlotResult:
    """The session is over. Give the slot back before its expiry would."""
    return schemas.CloudSlotResult(
        room_name=body.room_name, changed=await capacity.release(settings, body.room_name)
    )
