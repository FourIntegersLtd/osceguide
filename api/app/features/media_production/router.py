from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.tenancy import PlatformAdmin
from app.features.media_production import errors, schemas, service

router = APIRouter(tags=["media-production"])

Session = Annotated[AsyncSession, Depends(get_session)]

# The refusals any AV production route can return, alongside the shared Forbidden.
_PRODUCTION_ERRORS = (
    errors.ItemNotFound,
    errors.WrongMediaKind,
    errors.AvAlreadyRunning,
    errors.AvUnavailable,
)


# Starts narrating a summary item's text as a two-host podcast episode.
@router.post(
    "/media/{item_id}/generate-podcast",
    response_model=schemas.MediaRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Forbidden, *_PRODUCTION_ERRORS),
)
async def generate_summary_podcast(
    item_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.MediaRead:
    _ = admin
    return await service.enqueue_summary_podcast(session, item_id)


# Starts re-rendering a slide deck's narrated video after its slides have changed.
@router.post(
    "/media/{item_id}/regenerate-av",
    response_model=schemas.MediaRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Forbidden, *_PRODUCTION_ERRORS),
)
async def regenerate_slide_av(
    item_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.MediaRead:
    _ = admin
    return await service.enqueue_slide_regenerate(session, item_id)


# Starts voicing a podcast episode's script into an audio file.
@router.post(
    "/media/{item_id}/generate-audio",
    response_model=schemas.MediaRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Forbidden, *_PRODUCTION_ERRORS),
)
async def generate_podcast_audio(
    item_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.MediaRead:
    _ = admin
    return await service.enqueue_podcast_audio(session, item_id)
