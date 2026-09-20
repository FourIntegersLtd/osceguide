from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import Settings, get_settings
from app.features.media import errors as media_errors
from app.features.media import repository as media_repo
from app.features.media_production import domain
from app.features.media_production.errors import AvAlreadyRunning, WrongMediaKind
from app.features.media_production.repository import defer_job, lock_for_media


async def _load(session: AsyncSession, item_id: uuid.UUID):
    row = await media_repo.by_id(session, item_id)
    if row is None:
        raise media_errors.ItemNotFound()
    return row


def _content(row) -> dict[str, Any]:
    return dict(row.content or {})


async def _set_content(session: AsyncSession, item_id: uuid.UUID, content: dict[str, Any], status: str) -> None:
    merged = {**content, "status": status}
    await media_repo.update_item(session, item_id, content=merged)


async def enqueue_summary_podcast(session: AsyncSession, item_id: uuid.UUID) -> None:
    row = await _load(session, item_id)
    if row.kind != "summary":
        raise WrongMediaKind()
    content = _content(row)
    if domain.is_running(str(content.get("status"))):
        raise AvAlreadyRunning()
    await _set_content(session, item_id, content, domain.GENERATING_PODCAST)
    await defer_job(
        session,
        queue="media",
        task="produce_summary_podcast",
        args={"media_id": str(item_id)},
        queueing_lock=lock_for_media(item_id, "podcast"),
    )


async def enqueue_slide_regenerate(session: AsyncSession, item_id: uuid.UUID) -> None:
    row = await _load(session, item_id)
    if row.kind != "slide_deck":
        raise WrongMediaKind()
    content = _content(row)
    if domain.is_running(str(content.get("status"))):
        raise AvAlreadyRunning()
    await _set_content(session, item_id, content, domain.GENERATING_AUDIO)
    await defer_job(
        session,
        queue="media",
        task="regenerate_slide_av",
        args={"media_id": str(item_id)},
        queueing_lock=lock_for_media(item_id, "slides"),
    )


async def enqueue_podcast_audio(session: AsyncSession, item_id: uuid.UUID) -> None:
    row = await _load(session, item_id)
    if row.kind != "podcast":
        raise WrongMediaKind()
    content = _content(row)
    if domain.is_running(str(content.get("status"))):
        raise AvAlreadyRunning()
    await _set_content(session, item_id, content, domain.GENERATING_PODCAST)
    await defer_job(
        session,
        queue="media",
        task="produce_podcast_audio",
        args={"media_id": str(item_id)},
        queueing_lock=lock_for_media(item_id, "episode"),
    )


def work_dir(media_id: str) -> Path:
    return Path("/tmp/media_av") / media_id


async def run_summary_podcast_job(session: AsyncSession, media_id: uuid.UUID) -> None:
    from app.features.media_production.podcast_tts import produce_summary_podcast

    row = await _load(session, media_id)
    settings = get_settings()
    try:
        content = produce_summary_podcast(
            settings,
            title=row.title,
            content=_content(row),
            work_dir=work_dir(str(media_id)),
            media_id=str(media_id),
        )
        await media_repo.update_item(session, media_id, content=content)
    except Exception:
        content = _content(row)
        content["status"] = domain.FAILED
        await media_repo.update_item(session, media_id, content=content)
        raise


async def run_slide_av_job(session: AsyncSession, media_id: uuid.UUID) -> None:
    from app.features.catalog import repository as catalog_repo
    from app.features.media_production.slide_av import regenerate_slide_av

    row = await _load(session, media_id)
    settings = get_settings()
    wd = work_dir(str(media_id))
    content = _content(row)
    exam = await catalog_repo.exam_by_id(session, row.exam_id) if row.exam_id else None
    exam_code = exam.code if exam else None
    try:
        content = regenerate_slide_av(
            settings,
            content,
            wd,
            str(media_id),
            exam_code=exam_code,
        )
        await media_repo.update_item(session, media_id, content=content)
    except Exception:
        content = _content(await _load(session, media_id))
        content["status"] = domain.FAILED
        await media_repo.update_item(session, media_id, content=content)
        raise


async def run_podcast_audio_job(session: AsyncSession, media_id: uuid.UUID) -> None:
    from app.features.media_production.podcast_tts import produce_podcast_episode_audio

    row = await _load(session, media_id)
    settings = get_settings()
    try:
        content = produce_podcast_episode_audio(
            settings,
            title=row.title,
            content=_content(row),
            work_dir=work_dir(str(media_id)),
            media_id=str(media_id),
        )
        await media_repo.update_item(session, media_id, content=content)
    except Exception:
        content = _content(row)
        content["status"] = domain.FAILED
        await media_repo.update_item(session, media_id, content=content)
        raise
