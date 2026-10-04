"""The routes a platform admin uses to produce spoken material: checking its facts, writing and
checking its script, and then voicing it (narrating a summary as a podcast, re-rendering a slide
deck's video, or voicing a podcast episode). Voicing is refused until the script has been checked.
"""

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
# Voicing is also refused for words nobody has checked.
_VOICING_ERRORS = (*_PRODUCTION_ERRORS, errors.ScriptNotChecked)


# Starts checking an item's clinical claims against the guidelines; the result lands in its review.
@router.post(
    "/media/{item_id}/check-facts",
    response_model=schemas.MediaRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Forbidden, *_PRODUCTION_ERRORS),
)
async def check_media_facts(item_id: uuid.UUID, admin: PlatformAdmin, session: Session) -> schemas.MediaRead:
    return await service.enqueue_fact_check(session, item_id, requested_by=admin.user_id)


# Starts writing what an item will say and checking it against its source. Nothing is voiced.
@router.post(
    "/media/{item_id}/write-script",
    response_model=schemas.MediaRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Forbidden, *_PRODUCTION_ERRORS),
)
async def write_media_script(
    item_id: uuid.UUID, body: schemas.ScriptWriteRequest, admin: PlatformAdmin, session: Session
) -> schemas.MediaRead:
    return await service.enqueue_script_write(
        session, item_id, requested_by=admin.user_id, rewrite=body.rewrite
    )


# Starts narrating a summary item's text as a two-host podcast episode.
@router.post(
    "/media/{item_id}/generate-podcast",
    response_model=schemas.MediaRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Forbidden, *_VOICING_ERRORS),
)
async def generate_summary_podcast(
    item_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.MediaRead:
    return await service.enqueue_summary_podcast(session, item_id, requested_by=admin.user_id)


# Starts re-rendering a slide deck's narrated video after its slides have changed.
@router.post(
    "/media/{item_id}/regenerate-av",
    response_model=schemas.MediaRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Forbidden, *_VOICING_ERRORS),
)
async def regenerate_slide_av(
    item_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.MediaRead:
    return await service.enqueue_slide_regenerate(session, item_id, requested_by=admin.user_id)


# Starts voicing a podcast episode's script into an audio file.
@router.post(
    "/media/{item_id}/generate-audio",
    response_model=schemas.MediaRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Forbidden, *_VOICING_ERRORS),
)
async def generate_podcast_audio(
    item_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.MediaRead:
    return await service.enqueue_podcast_audio(session, item_id, requested_by=admin.user_id)
