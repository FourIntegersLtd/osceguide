from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.tenancy import PlatformAdmin
from app.features.media import errors as media_errors
from app.features.media import service as media_service
from app.features.media.schemas import MediaRead
from app.features.media_production import service as production_service
from app.features.media_production.errors import AvAlreadyRunning, AvUnavailable, WrongMediaKind

router = APIRouter(tags=["media-production"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/media/{item_id}/generate-podcast",
    response_model=MediaRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(
        Forbidden,
        media_errors.ItemNotFound,
        WrongMediaKind,
        AvAlreadyRunning,
        AvUnavailable,
    ),
)
async def generate_summary_podcast(
    item_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> MediaRead:
    await production_service.enqueue_summary_podcast(session, item_id)
    return await media_service.read_by_id(session, item_id, viewer_is_admin=True)


@router.post(
    "/media/{item_id}/regenerate-av",
    response_model=MediaRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(
        Forbidden,
        media_errors.ItemNotFound,
        WrongMediaKind,
        AvAlreadyRunning,
        AvUnavailable,
    ),
)
async def regenerate_slide_av(item_id: uuid.UUID, admin: PlatformAdmin, session: Session) -> MediaRead:
    await production_service.enqueue_slide_regenerate(session, item_id)
    return await media_service.read_by_id(session, item_id, viewer_is_admin=True)


@router.post(
    "/media/{item_id}/generate-audio",
    response_model=MediaRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(
        Forbidden,
        media_errors.ItemNotFound,
        WrongMediaKind,
        AvAlreadyRunning,
        AvUnavailable,
    ),
)
async def generate_podcast_audio(item_id: uuid.UUID, admin: PlatformAdmin, session: Session) -> MediaRead:
    await production_service.enqueue_podcast_audio(session, item_id)
    return await media_service.read_by_id(session, item_id, viewer_is_admin=True)
