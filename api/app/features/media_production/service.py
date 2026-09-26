from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.features.catalog import service as catalog
from app.features.media import service as media_service
from app.features.media.service import production_item, replace_content
from app.features.media_production import domain
from app.features.media_production.errors import AvAlreadyRunning, WrongMediaKind
from app.features.media_production.repository import defer_job, lock_for_media
from app.features.media_production.schemas import MediaRead


async def _set_status(
    session: AsyncSession, item_id: uuid.UUID, content: dict[str, Any], status: str
) -> None:
    await replace_content(session, item_id, {**content, "status": status})


async def _read(session: AsyncSession, item_id: uuid.UUID) -> MediaRead:
    item = await media_service.read_by_id(session, item_id, viewer_is_admin=True)
    return MediaRead.model_validate(item.model_dump())


async def enqueue_summary_podcast(session: AsyncSession, item_id: uuid.UUID) -> MediaRead:
    item = await production_item(session, item_id)
    if item.kind != "summary":
        raise WrongMediaKind()
    if domain.is_running(str(item.content.get("status"))):
        raise AvAlreadyRunning()
    await _set_status(session, item_id, item.content, domain.GENERATING_PODCAST)
    await defer_job(
        session,
        queue="media",
        task="produce_summary_podcast",
        args={"media_id": str(item_id)},
        queueing_lock=lock_for_media(item_id, "podcast"),
    )
    return await _read(session, item_id)


async def enqueue_slide_regenerate(session: AsyncSession, item_id: uuid.UUID) -> MediaRead:
    item = await production_item(session, item_id)
    if item.kind != "slide_deck":
        raise WrongMediaKind()
    if domain.is_running(str(item.content.get("status"))):
        raise AvAlreadyRunning()
    await _set_status(session, item_id, item.content, domain.GENERATING_AUDIO)
    await defer_job(
        session,
        queue="media",
        task="regenerate_slide_av",
        args={"media_id": str(item_id)},
        queueing_lock=lock_for_media(item_id, "slides"),
    )
    return await _read(session, item_id)


async def enqueue_podcast_audio(session: AsyncSession, item_id: uuid.UUID) -> MediaRead:
    item = await production_item(session, item_id)
    if item.kind != "podcast":
        raise WrongMediaKind()
    if domain.is_running(str(item.content.get("status"))):
        raise AvAlreadyRunning()
    await _set_status(session, item_id, item.content, domain.GENERATING_PODCAST)
    await defer_job(
        session,
        queue="media",
        task="produce_podcast_audio",
        args={"media_id": str(item_id)},
        queueing_lock=lock_for_media(item_id, "episode"),
    )
    return await _read(session, item_id)


def work_dir(media_id: str) -> Path:
    return Path(tempfile.gettempdir()) / "media_av" / media_id


async def run_summary_podcast_job(session: AsyncSession, media_id: uuid.UUID) -> None:
    from app.features.media_production.podcast_tts import produce_summary_podcast

    item = await production_item(session, media_id)
    settings = get_settings()
    try:
        content = produce_summary_podcast(
            settings,
            title=item.title,
            content=item.content,
            work_dir=work_dir(str(media_id)),
            media_id=str(media_id),
        )
        await replace_content(session, media_id, content)
    except Exception:
        failed = dict(item.content)
        failed["status"] = domain.FAILED
        await replace_content(session, media_id, failed)
        raise


async def run_slide_av_job(session: AsyncSession, media_id: uuid.UUID) -> None:
    from app.features.media_production.slide_av import regenerate_slide_av

    item = await production_item(session, media_id)
    settings = get_settings()
    job_work_dir = work_dir(str(media_id))
    exam_code = await catalog.exam_code_by_id(session, item.exam_id) if item.exam_id else None
    try:
        content = regenerate_slide_av(
            settings,
            item.content,
            job_work_dir,
            str(media_id),
            exam_code=exam_code,
        )
        await replace_content(session, media_id, content)
    except Exception:
        # Re-read the item: the render may have already written partial content
        # we still want preserved alongside the failed status.
        current = await production_item(session, media_id)
        failed = dict(current.content)
        failed["status"] = domain.FAILED
        await replace_content(session, media_id, failed)
        raise


async def run_podcast_audio_job(session: AsyncSession, media_id: uuid.UUID) -> None:
    from app.features.media_production.podcast_tts import produce_podcast_episode_audio

    item = await production_item(session, media_id)
    settings = get_settings()
    try:
        content = produce_podcast_episode_audio(
            settings,
            title=item.title,
            content=item.content,
            work_dir=work_dir(str(media_id)),
            media_id=str(media_id),
        )
        await replace_content(session, media_id, content)
    except Exception:
        failed = dict(item.content)
        failed["status"] = domain.FAILED
        await replace_content(session, media_id, failed)
        raise
