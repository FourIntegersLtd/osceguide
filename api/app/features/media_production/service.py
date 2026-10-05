"""Enqueues production jobs against a media item, and runs each job's actual work: checking its
facts, writing and checking what will be spoken, and then the voicing itself (narrating a summary
as a podcast, re-rendering a slide deck's video, or voicing a podcast episode).

Voicing is the step that costs money, so it is refused until the words it would speak are the
words that were last checked.
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from pathlib import Path
from typing import Any, BinaryIO

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import publish_after_commit, user_topic
from app.core.logging import get_logger
from app.core.ports import GuidelineIndex, GuidelineWeb
from app.core.settings import Settings, get_settings
from app.features.catalog import service as catalog
from app.features.media import service as media_service
from app.features.media.service import production_item, replace_content
from app.features.media_production import domain, script_check, service_facts
from app.features.media_production.errors import AvAlreadyRunning, ScriptNotChecked, WrongMediaKind
from app.features.media_production.repository import defer_job, lock_for_media
from app.features.media_production.s3 import delete_object, upload_fileobj
from app.features.media_production.schemas import MediaRead
from app.features.media_production.slide_narration import READER_MODEL
from app.features.media_production.slide_narration import complete as model_reply

log = get_logger(__name__)

# Published to the requesting admin's `/me/events` topic once a production job
# settles, success or failure, so `MediaDetailScreen` learns without polling.
MEDIA_UPDATED = "media.updated"
# The kinds of item that are spoken, and so are checked before they are.
CHECKED_KINDS = frozenset({"slide_deck", "summary", "podcast"})
_ERROR_CHARACTERS = 300


async def _set_status(
    session: AsyncSession, item_id: uuid.UUID, content: dict[str, Any], status: str
) -> None:
    """Rewrites an item's stored content with a new production status, leaving the rest as it was."""
    await replace_content(session, item_id, {**content, "status": status})


async def read_item(session: AsyncSession, item_id: uuid.UUID) -> MediaRead:
    """Re-reads an item as the production schema's own `MediaRead`, after a status change."""
    item = await media_service.read_by_id(session, item_id, viewer_is_admin=True)
    return MediaRead.model_validate(item.model_dump())


async def enqueue_summary_podcast(
    session: AsyncSession, item_id: uuid.UUID, *, requested_by: uuid.UUID
) -> MediaRead:
    """Starts turning a summary into a podcast, refusing the wrong kind of item or a job already running."""
    item = await production_item(session, item_id)
    if item.kind != "summary":
        raise WrongMediaKind()
    if domain.is_running(str(item.content.get("status"))):
        raise AvAlreadyRunning()
    if not script_check.is_checked(item.kind, item.content):
        raise ScriptNotChecked()
    await _set_status(session, item_id, item.content, domain.GENERATING_PODCAST)
    await defer_job(
        session,
        queue="media",
        task="produce_summary_podcast",
        args={"media_id": str(item_id), "requested_by": str(requested_by)},
        queueing_lock=lock_for_media(item_id, "podcast"),
    )
    return await read_item(session, item_id)


async def enqueue_slide_regenerate(
    session: AsyncSession, item_id: uuid.UUID, *, requested_by: uuid.UUID
) -> MediaRead:
    """Starts re-rendering a slide deck's narrated video, refusing the wrong kind or a job already running."""
    item = await production_item(session, item_id)
    if item.kind != "slide_deck":
        raise WrongMediaKind()
    if domain.is_running(str(item.content.get("status"))):
        raise AvAlreadyRunning()
    if not script_check.is_checked(item.kind, item.content):
        raise ScriptNotChecked()
    await _set_status(session, item_id, item.content, domain.GENERATING_AUDIO)
    await defer_job(
        session,
        queue="media",
        task="regenerate_slide_av",
        args={"media_id": str(item_id), "requested_by": str(requested_by)},
        queueing_lock=lock_for_media(item_id, "slides"),
    )
    return await read_item(session, item_id)


async def enqueue_podcast_audio(
    session: AsyncSession, item_id: uuid.UUID, *, requested_by: uuid.UUID
) -> MediaRead:
    """Starts voicing a podcast episode's script, refusing the wrong kind of item or a job already running."""
    item = await production_item(session, item_id)
    if item.kind != "podcast":
        raise WrongMediaKind()
    if domain.is_running(str(item.content.get("status"))):
        raise AvAlreadyRunning()
    if not script_check.is_checked(item.kind, item.content):
        raise ScriptNotChecked()
    await _set_status(session, item_id, item.content, domain.GENERATING_PODCAST)
    await defer_job(
        session,
        queue="media",
        task="produce_podcast_audio",
        args={"media_id": str(item_id), "requested_by": str(requested_by)},
        queueing_lock=lock_for_media(item_id, "episode"),
    )
    return await read_item(session, item_id)


async def _checkable_item(session: AsyncSession, item_id: uuid.UUID) -> Any:
    """The item, if it is a kind whose facts are checked and no job is working on it."""
    item = await production_item(session, item_id)
    if item.kind not in CHECKED_KINDS:
        raise WrongMediaKind()
    if domain.is_running(str(item.content.get("status"))):
        raise AvAlreadyRunning()
    return item


async def enqueue_fact_check(
    session: AsyncSession, item_id: uuid.UUID, *, requested_by: uuid.UUID
) -> MediaRead:
    """Starts checking an item's clinical claims against the guidelines.

    The item's status goes back to what it was once the check settles: checking facts changes
    nothing a learner is served.
    """
    item = await _checkable_item(session, item_id)
    previous = item.content.get("status")
    await _set_status(session, item_id, item.content, domain.CHECKING_FACTS)
    await defer_job(
        session,
        queue="media",
        task="check_media_facts",
        args={
            "media_id": str(item_id),
            "requested_by": str(requested_by),
            "previous_status": previous if isinstance(previous, str) else None,
        },
        queueing_lock=lock_for_media(item_id, "facts"),
    )
    return await read_item(session, item_id)


async def record_hand_check(
    session: AsyncSession, item_id: uuid.UUID, claims: list[dict[str, Any]], *, checked_by: uuid.UUID
) -> MediaRead:
    """Stores a fact check a person did themselves in the item's review, in place of the platform's
    check, which it replaces. Nothing else on the item changes."""
    item = await _checkable_item(session, item_id)
    content = dict(item.content)
    sections = service_facts.sections_of(item.kind, item.title, content)
    facts = service_facts.checked_by_hand(sections, claims, checked_by=str(checked_by))
    review = dict(content.get("review") or {})
    # A failed platform check left its error here; the hand check replaces that check, so the
    # error would otherwise sit beside a passing review.
    review.pop("error", None)
    content["review"] = {**review, "facts": facts}
    await replace_content(session, item_id, content)
    return await read_item(session, item_id)


async def enqueue_script_write(
    session: AsyncSession, item_id: uuid.UUID, *, requested_by: uuid.UUID, rewrite: bool
) -> MediaRead:
    """Starts writing what an item will say, and checking it, without voicing any of it.

    `rewrite` throws away the lines already written; otherwise only what is missing or out of
    date is written, and everything is checked.
    """
    item = await production_item(session, item_id)
    if item.kind not in CHECKED_KINDS:
        raise WrongMediaKind()
    if domain.is_running(str(item.content.get("status"))):
        raise AvAlreadyRunning()
    await _set_status(session, item_id, item.content, domain.WRITING_SCRIPT)
    await defer_job(
        session,
        queue="media",
        task="write_media_script",
        args={"media_id": str(item_id), "requested_by": str(requested_by), "rewrite": rewrite},
        queueing_lock=lock_for_media(item_id, "script"),
    )
    return await read_item(session, item_id)


def is_running(content: dict[str, Any]) -> bool:
    """Whether a job is working on an item with this content, so nobody else should rewrite it."""
    return domain.is_running(str(content.get("status")))


def work_dir(media_id: str) -> Path:
    """The scratch directory a production job renders its files into before they are uploaded."""
    return Path(tempfile.gettempdir()) / "media_av" / media_id


def upload_image(settings: Settings, content: BinaryIO, key: str) -> str:
    """Uploads an image (e.g. an avatar) to this slice's bucket.

    Exposed for `identity`, which owns no storage of its own.
    """
    return upload_fileobj(settings, content, key)


def delete_image(settings: Settings, url: str) -> None:
    """Deletes a previously uploaded image. Exposed for `identity`, same as `upload_image`."""
    delete_object(settings, url)


def _voice_dir(media_id: str) -> Path:
    """Where a deck's voiced lines are kept between runs, so a second render pays only for the
    lines that changed. Outside `work_dir`, which every run empties."""
    return Path(tempfile.gettempdir()) / "media_av_voice" / media_id


def second_reader(settings: Settings, system: str) -> script_check.Complete:
    """The model that checks the script: GPT-5, not the writer's o3, with Claude if it is unavailable."""
    return lambda prompt: model_reply(settings, prompt, system=system, openai_model=READER_MODEL)


def with_error(content: dict[str, Any], step: str, error: Exception) -> dict[str, Any]:
    """`content` with why a check failed kept in its review, for the staff screen to show."""
    review = dict(content.get("review") or {})
    review["error"] = {"step": step, "message": str(error)[:_ERROR_CHARACTERS] or type(error).__name__}
    return {**content, "review": review}


async def run_fact_check_job(
    session: AsyncSession,
    media_id: uuid.UUID,
    *,
    requested_by: uuid.UUID,
    previous_status: str | None,
    guidelines: GuidelineIndex | None = None,
    web: GuidelineWeb | None = None,
    complete: script_check.Complete | None = None,
    progress: service_facts.Progress | None = None,
) -> None:
    """Checks an item's clinical claims and stores the result in its review, changing nothing else.

    The library, the web search and the model are this deployment's unless a test hands in its own.
    """
    item = await production_item(session, media_id)
    content = dict(item.content)
    try:
        facts = await service_facts.check_as_deployed(
            title=item.title,
            sections=service_facts.sections_of(item.kind, item.title, content),
            guidelines=guidelines,
            web=web,
            complete=complete,
            on_progress=progress,
        )
        review = dict(content.get("review") or {})
        review.pop("error", None)
        content["review"] = {**review, "facts": facts}
    except Exception as error:  # noqa: BLE001 - any failure is recorded on the item for the staff screen
        log.warning("fact check failed", media_id=str(media_id), error=str(error))
        content = with_error(content, "facts", error)
    if previous_status is None:
        content.pop("status", None)
    else:
        content["status"] = previous_status
    await replace_content(session, media_id, content)
    publish_after_commit(session, user_topic(requested_by), MEDIA_UPDATED, {"media_id": str(media_id)})


async def save_fact_progress(
    session: AsyncSession, media_id: uuid.UUID, *, requested_by: uuid.UUID, facts: dict[str, Any]
) -> None:
    """Keeps a running check's claims so far on the item and tells whoever asked, so their screen
    fills in as each claim is judged rather than all at once at the end."""
    item = await production_item(session, media_id)
    content = dict(item.content)
    content["review"] = {**(content.get("review") or {}), "facts": facts}
    await replace_content(session, media_id, content)
    publish_after_commit(session, user_topic(requested_by), MEDIA_UPDATED, {"media_id": str(media_id)})


async def run_script_write_job(
    session: AsyncSession,
    media_id: uuid.UUID,
    *,
    requested_by: uuid.UUID,
    rewrite: bool,
    complete: script_check.Complete | None = None,
) -> None:
    """Writes and checks what an item will say, leaving it awaiting review. Nothing is voiced.

    The checking model is this deployment's unless a test hands in its own.
    """
    item = await production_item(session, media_id)
    settings = get_settings()
    reader = complete or second_reader(settings, script_check.CHECK_SYSTEM)
    try:
        if item.kind == "slide_deck":
            content = await asyncio.to_thread(
                script_check.prepare_deck, settings, item.content, rewrite=rewrite, complete=reader
            )
        else:
            content = await asyncio.to_thread(
                script_check.prepare_podcast,
                settings,
                kind=item.kind,
                title=item.title,
                content=item.content,
                rewrite=rewrite,
                complete=reader,
            )
        content["status"] = domain.AWAITING_REVIEW
    except Exception as error:  # noqa: BLE001 - any failure is recorded on the item as failed
        log.warning("script write failed", media_id=str(media_id), error=str(error))
        content = {**with_error(item.content, "script", error), "status": domain.FAILED}
    await replace_content(session, media_id, content)
    publish_after_commit(session, user_topic(requested_by), MEDIA_UPDATED, {"media_id": str(media_id)})


async def run_summary_podcast_job(
    session: AsyncSession, media_id: uuid.UUID, *, requested_by: uuid.UUID
) -> None:
    """Renders a summary item's podcast audio and stores it, marking the item failed if that throws."""
    from app.features.media_production.podcast_tts import produce_summary_podcast

    item = await production_item(session, media_id)
    settings = get_settings()
    try:
        content = await asyncio.to_thread(
            produce_summary_podcast,
            settings,
            title=item.title,
            content=item.content,
            work_dir=work_dir(str(media_id)),
            media_id=str(media_id),
        )
        await replace_content(session, media_id, content)
    except Exception:  # noqa: BLE001 - any render failure is recorded on the item as failed
        failed = dict(item.content)
        failed["status"] = domain.FAILED
        await replace_content(session, media_id, failed)
    publish_after_commit(session, user_topic(requested_by), MEDIA_UPDATED, {"media_id": str(media_id)})


async def run_slide_av_job(session: AsyncSession, media_id: uuid.UUID, *, requested_by: uuid.UUID) -> None:
    """Re-renders a slide deck's narrated video and stores it, marking the item failed if that throws."""
    from app.features.media_production.slide_av import regenerate_slide_av

    item = await production_item(session, media_id)
    settings = get_settings()
    job_work_dir = work_dir(str(media_id))
    exam_code = await catalog.exam_code_by_id(session, item.exam_id) if item.exam_id else None
    try:
        # In a thread: a render takes minutes, and on the event loop it stalls every other job.
        content = await asyncio.to_thread(
            regenerate_slide_av,
            settings,
            item.content,
            job_work_dir,
            str(media_id),
            exam_code=exam_code,
            voice_dir=_voice_dir(str(media_id)),
        )
        await replace_content(session, media_id, content)
    except Exception:  # noqa: BLE001 - any render failure is recorded on the item as failed
        # Re-read the item: the render may have already written partial content
        # we still want preserved alongside the failed status.
        current = await production_item(session, media_id)
        failed = dict(current.content)
        failed["status"] = domain.FAILED
        await replace_content(session, media_id, failed)
    publish_after_commit(session, user_topic(requested_by), MEDIA_UPDATED, {"media_id": str(media_id)})


async def run_podcast_audio_job(
    session: AsyncSession, media_id: uuid.UUID, *, requested_by: uuid.UUID
) -> None:
    """Renders a podcast episode's audio and stores it, marking the item failed if that throws."""
    from app.features.media_production.podcast_tts import produce_podcast_episode_audio

    item = await production_item(session, media_id)
    settings = get_settings()
    try:
        content = await asyncio.to_thread(
            produce_podcast_episode_audio,
            settings,
            title=item.title,
            content=item.content,
            work_dir=work_dir(str(media_id)),
            media_id=str(media_id),
        )
        await replace_content(session, media_id, content)
    except Exception:  # noqa: BLE001 - any render failure is recorded on the item as failed
        failed = dict(item.content)
        failed["status"] = domain.FAILED
        await replace_content(session, media_id, failed)
    publish_after_commit(session, user_topic(requested_by), MEDIA_UPDATED, {"media_id": str(media_id)})
