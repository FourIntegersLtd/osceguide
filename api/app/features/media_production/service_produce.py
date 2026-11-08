"""Starts, stops and runs the agent that produces a media item or a platform station from a brief.

A run is long, so it never holds one transaction open: each step's result is saved in its own
unit of work, which is also where the run learns that staff asked it to stop or that another run
has taken the item over. A run is known by an id kept in the item's review; a job whose id is no
longer the stored one does nothing more.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, ParamSpec, TypeVar

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import publish_after_commit, user_topic
from app.core.logging import get_logger
from app.core.schemas import StationReview
from app.core.settings import Settings, get_settings
from app.features.catalog import service as catalog
from app.features.generation import service as generation
from app.features.media.service import production_item, replace_content, replace_title
from app.features.media_production import agent_loop, domain, script_check, service_facts, slide_pictures
from app.features.media_production.errors import (
    AvAlreadyRunning,
    FactCheckRunning,
    NotEditableError,
    StationBeingProduced,
    StationHasNoTemplate,
    StationNotEditable,
    WrongMediaKind,
)
from app.features.media_production.jobs import PRODUCE_QUEUE
from app.features.media_production.produce import Draft, Kit, Production, brief_record, run_of
from app.features.media_production.repository import defer_job
from app.features.media_production.schemas import MediaRead
from app.features.media_production.service import (
    CHECKED_KINDS,
    MEDIA_UPDATED,
    is_running,
    read_item,
    second_reader,
    with_error,
)
from app.features.stations import service_facts as station_facts

log = get_logger(__name__)

# A run saves after every tool call, and its slowest tool takes a few minutes. One silent for
# this long has lost its worker, so the item may be produced again.
STALE_SECONDS = 900

# Opens a unit of work that commits when it closes: the job's own, or a test's.
Sessions = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@dataclass(frozen=True)
class Subject:
    """What a run produces, as it reads it: `content` is the working copy, its review inside it."""

    kind: str
    title: str
    exam_id: uuid.UUID | None
    content: dict[str, Any]
    template_version_id: uuid.UUID | None = None
    # A station's management plan fields, the only ones its facts are checked in.
    checked_fields: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Target:
    """Where a run's subject is read from and kept: a media item or a platform station version."""

    # Reads the subject; `True` locks it until the unit of work ends.
    read: Callable[[AsyncSession, uuid.UUID, bool], Awaitable[Subject]]
    # Keeps the working copy and tells whoever asked (the last argument).
    write: Callable[[AsyncSession, uuid.UUID, dict[str, Any], uuid.UUID], Awaitable[None]]
    # The status a finished run leaves, from the subject's kind and content.
    done: Callable[[str, dict[str, Any]], str | None]
    # The status a failed run leaves; why it failed is kept in the review either way.
    failed: str | None
    # Gives an untitled subject the title its draft chose; None where the title is not the run's to set.
    rename: Callable[[AsyncSession, uuid.UUID, str], Awaitable[None]] | None
    # The job that runs it, and the name its id is handed to the job under.
    task: str
    key: str


async def _read_media(session: AsyncSession, media_id: uuid.UUID, lock: bool) -> Subject:
    """A media item as the agent works on it."""
    item = await production_item(session, media_id, lock=lock)
    return Subject(kind=item.kind, title=item.title, exam_id=item.exam_id, content=item.content)


async def _write_media(
    session: AsyncSession, media_id: uuid.UUID, content: dict[str, Any], requested_by: uuid.UUID
) -> None:
    """Keeps a media item's working copy and tells whoever asked."""
    await replace_content(session, media_id, content)
    publish_after_commit(session, user_topic(requested_by), MEDIA_UPDATED, {"media_id": str(media_id)})


async def _read_station(session: AsyncSession, version_id: uuid.UUID, lock: bool) -> Subject:
    """A platform station version as the agent works on it."""
    found = await station_facts.production_version(session, version_id, lock=lock)
    return Subject(
        kind="station",
        title=found.title,
        exam_id=found.exam_id,
        content=found.content,
        template_version_id=found.template_version_id,
        checked_fields=found.checked_fields,
    )


async def _write_station(
    session: AsyncSession, version_id: uuid.UUID, content: dict[str, Any], requested_by: uuid.UUID
) -> None:
    """Keeps a station version's working copy and tells whoever asked."""
    await station_facts.save_production(session, version_id, content, requested_by=requested_by)


def _media_done(kind: str, content: dict[str, Any]) -> str | None:
    """An item whose script was checked waits for staff to voice it; anything else is a draft."""
    return domain.AWAITING_REVIEW if script_check.is_checked(kind, content) else None


MEDIA = Target(
    read=_read_media,
    write=_write_media,
    rename=replace_title,
    done=_media_done,
    failed=domain.FAILED,
    task="produce_media",
    key="media_id",
)
# A station is never voiced, so it ends as a plain draft either way.
STATION = Target(
    read=_read_station,
    write=_write_station,
    rename=None,
    done=lambda kind, content: None,
    failed=None,
    task="produce_station",
    key="version_id",
)


def _abandoned(content: dict[str, Any], now: datetime) -> bool:
    """Whether the item is being produced by a run that has stopped saving."""
    if content.get("status") != domain.PRODUCING:
        return False
    try:
        last = datetime.fromisoformat(str(run_of(content).get("heartbeat_at")))
    except ValueError:
        return True
    return (now - last).total_seconds() > STALE_SECONDS


async def enqueue_produce(
    session: AsyncSession,
    item_id: uuid.UUID,
    *,
    requested_by: uuid.UUID,
    brief: str,
    now: datetime | None = None,
) -> MediaRead:
    """Starts the agent on a draft, refusing a published item, a kind that is never spoken, or an
    item something is already working on. A run whose worker has died is taken over."""
    current = now or datetime.now(UTC)
    item = await production_item(session, item_id, lock=True)
    if item.kind not in CHECKED_KINDS:
        raise WrongMediaKind()
    if not item.editable:
        raise NotEditableError()
    if is_running(item.content) and not _abandoned(item.content, current):
        raise AvAlreadyRunning()
    await _start(session, MEDIA, item_id, item.content, requested_by, brief_record(brief), current)
    return await read_item(session, item_id)


async def enqueue_station_produce(
    session: AsyncSession,
    station_id: uuid.UUID,
    version: int,
    *,
    requested_by: uuid.UUID,
    brief: str,
    now: datetime | None = None,
) -> StationReview:
    """Starts the agent on a platform station's draft version, as on a media item. A station with no
    template cannot be drafted, and one being checked or produced is left alone unless its run died."""
    current = now or datetime.now(UTC)
    station = await station_facts.production_of(session, station_id, version, lock=True)
    if not station.editable:
        raise StationNotEditable()
    if station.template_version_id is None:
        raise StationHasNoTemplate()
    status = station.content.get("status")
    if status == station_facts.CHECKING:
        raise FactCheckRunning()
    if status == station_facts.PRODUCING and not _abandoned(station.content, current):
        raise StationBeingProduced()
    brief_kept = brief_record(brief)
    await _start(session, STATION, station.version_id, station.content, requested_by, brief_kept, current)
    return await station_facts.read_review(session, station_id, version)


async def _start(
    session: AsyncSession,
    target: Target,
    subject_id: uuid.UUID,
    content: dict[str, Any],
    requested_by: uuid.UUID,
    brief: dict[str, Any],
    now: datetime,
) -> None:
    """Keeps the brief and a fresh run record on the subject, drops any old error, and queues the run.
    No queueing lock: a job left queued by a dead worker must not block the run that replaces it."""
    review = dict(content.get("review") or {})
    review.pop("error", None)
    run_id = uuid.uuid4().hex
    started = now.isoformat()
    review["brief"] = brief
    review["run"] = {"id": run_id, "started_at": started, "heartbeat_at": started, "steps": []}
    await target.write(
        session, subject_id, {**content, "review": review, "status": domain.PRODUCING}, requested_by
    )
    await defer_job(
        session,
        queue=PRODUCE_QUEUE,
        task=target.task,
        args={target.key: str(subject_id), "requested_by": str(requested_by), "run_id": run_id},
    )


async def _ask_stop(
    session: AsyncSession, target: Target, subject_id: uuid.UUID, requested_by: uuid.UUID
) -> None:
    """Marks a running agent's run to stop after the step it is on. Does nothing if none is running."""
    subject = await target.read(session, subject_id, True)
    if subject.content.get("status") == domain.PRODUCING:
        review = dict(subject.content.get("review") or {})
        review["run"] = {**run_of(subject.content), "stop": True}
        await target.write(session, subject_id, {**subject.content, "review": review}, requested_by)


async def stop_produce(session: AsyncSession, item_id: uuid.UUID, *, requested_by: uuid.UUID) -> MediaRead:
    """Asks the agent producing a media item to stop after the step it is on."""
    await _ask_stop(session, MEDIA, item_id, requested_by)
    return await read_item(session, item_id)


async def stop_station_produce(
    session: AsyncSession, station_id: uuid.UUID, version: int, *, requested_by: uuid.UUID
) -> StationReview:
    """Asks the agent producing a station version to stop after the step it is on."""
    station = await station_facts.production_of(session, station_id, version)
    await _ask_stop(session, STATION, station.version_id, requested_by)
    return await station_facts.read_review(session, station_id, version)


def _deployed_draft(subject: Subject, exam_code: str | None, settings: Settings, sessions: Sessions) -> Draft:
    """This deployment's generator for one kind of item."""
    kind = subject.kind

    async def draft(prompt: str) -> dict[str, Any]:
        """A fresh draft from `prompt`, in the keys the item's content uses."""
        if kind == "station" and subject.template_version_id is not None:
            async with sessions() as session:
                return await station_facts.draft_production(
                    session, subject.template_version_id, prompt, settings
                )
        # Deck and podcast read nothing from the database: no session, so no pooled connection sits idle.
        if kind == "slide_deck":
            return await generation.generate_slide_deck(
                prompt=prompt, exam_code=exam_code, session=None, settings=settings
            )
        if kind == "podcast":
            return await generation.generate_podcast(
                prompt=prompt, exam_code=exam_code, session=None, settings=settings
            )
        async with sessions() as session:
            return await generation.generate_summary(
                prompt=prompt, exam_code=exam_code, session=session, settings=settings
            )

    return draft


_Params = ParamSpec("_Params")
_Returned = TypeVar("_Returned")


def _threaded(blocking: Callable[_Params, _Returned]) -> Callable[_Params, Awaitable[_Returned]]:
    """`blocking` run on a thread, so a tool's slow call does not hold up the event loop."""

    async def call(*args: _Params.args, **kwargs: _Params.kwargs) -> _Returned:
        """Runs the blocking call on a worker thread and awaits it."""
        return await asyncio.to_thread(blocking, *args, **kwargs)

    return call


def _commons() -> httpx.Client:
    """A client Wikimedia will answer: it asks every caller to say who it is."""
    return httpx.Client(headers={"User-Agent": slide_pictures.USER_AGENT}, timeout=60, follow_redirects=True)


def deployed_kit(subject: Subject, exam_code: str | None, settings: Settings, sessions: Sessions) -> Kit:
    """This deployment's services for the producing line. Blocking work runs on a thread."""
    kind, title = subject.kind, subject.title
    reader = second_reader(settings, script_check.CHECK_SYSTEM)

    async def check_facts(
        title: str, sections: list[service_facts.Section], earlier: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return await service_facts.check_as_deployed(title=title, sections=sections, earlier=earlier)

    def script(content: dict[str, Any], rewrite: bool) -> dict[str, Any]:
        """Writes and reads the script of a deck, or the dialogue of anything else."""
        if kind == "slide_deck":
            return script_check.prepare_deck_to_time(settings, content, rewrite=rewrite, complete=reader)
        return script_check.prepare_podcast(
            settings,
            kind=kind,
            title=title,
            content=content,
            rewrite=rewrite,
            complete=reader,
        )

    def search(query: str) -> list[tuple[slide_pictures.Candidate, bytes]]:
        """Commons pictures for a search, each fetched so the agent can look at it."""
        with _commons() as http:
            found = []
            for candidate in slide_pictures.commons_search(http, query):
                fetched = http.get(candidate.url)
                if fetched.is_success:
                    found.append((candidate, fetched.content))
            return found

    def store(candidate: slide_pictures.Candidate | str) -> str:
        """Keeps a chosen picture in the bucket the renderer draws from."""
        if isinstance(candidate, str):
            return slide_pictures.store_library_picture(settings, candidate)
        with _commons() as http:
            return slide_pictures.store_picture(settings, http, candidate)

    def check(content: dict[str, Any]) -> dict[str, Any]:
        """Reads the script again as it stands, correcting nothing."""
        if kind == "slide_deck":
            return script_check.check_deck(reader, content, written=frozenset(), plan_written=False)
        return script_check.prepare_podcast(
            settings, kind=kind, title=title, content=content, rewrite=False, complete=reader
        )

    return Kit(
        draft=_deployed_draft(subject, exam_code, settings, sessions),
        check_facts=check_facts,
        write_script=_threaded(script),
        check_script=_threaded(check),
        search_pictures=_threaded(search),
        store_picture=_threaded(store),
    )


async def _save(
    sessions: Sessions,
    target: Target,
    subject_id: uuid.UUID,
    run_id: str,
    content: dict[str, Any],
    *,
    requested_by: uuid.UUID,
    status: str | None,
    title: str | None = None,
) -> bool:
    """Stores the run's working copy and tells whoever asked. Answers whether the run should go on:
    not once staff have asked it to stop, and not once another run owns the item, when nothing is
    written at all."""
    async with sessions() as session:
        stored = run_of((await target.read(session, subject_id, True)).content)
        if stored.get("id") != run_id:
            return False
        stopping = bool(stored.get("stop"))
        run = {**run_of(content), "heartbeat_at": datetime.now(UTC).isoformat()}
        if stopping and status == domain.PRODUCING:
            run["stop"] = True
        saved = {**content, "review": {**(content.get("review") or {}), "run": run}}
        saved.pop("status", None)
        if status is not None:
            saved["status"] = status
        if title and target.rename:
            await target.rename(session, subject_id, title)
        await target.write(session, subject_id, saved, requested_by)
    return not stopping


async def run_produce_job(
    subject_id: uuid.UUID,
    *,
    requested_by: uuid.UUID,
    run_id: str,
    sessions: Sessions,
    target: Target = MEDIA,
    turn: agent_loop.Turn | None = None,
    kit: Kit | None = None,
    limits: agent_loop.Limits | None = None,
) -> None:
    """Runs the agent over one item or station until it finishes, is stopped or reaches a limit.

    An item ends awaiting review when what it will say has been checked, and otherwise as a plain
    draft with what is outstanding listed; a station always ends as a draft. The model and the
    generator are this deployment's unless a test hands in its own kit.
    """
    async with sessions() as session:
        subject = await target.read(session, subject_id, False)
        if subject.content.get("status") != domain.PRODUCING or run_of(subject.content).get("id") != run_id:
            return
        exam_code = await catalog.exam_code_by_id(session, subject.exam_id) if subject.exam_id else None
    settings = get_settings()
    production = Production(
        kind=subject.kind,
        title=subject.title,
        content=subject.content,
        kit=kit or deployed_kit(subject, exam_code, settings, sessions),
        checked_fields=subject.checked_fields,
    )

    async def save(content: dict[str, Any], status: str | None) -> bool:
        """Keeps the working copy with `status`, answering whether to go on."""
        return await _save(
            sessions,
            target,
            subject_id,
            run_id,
            content,
            requested_by=requested_by,
            status=status,
            title=production.named,
        )

    async def on_step(tool: str, text: str, tokens: int) -> bool:
        """Logs one tool call and saves, answering whether to go on."""
        production.log(tool, text, tokens)
        return await save(production.content, domain.PRODUCING)

    try:
        result = await production.produce(
            turn or agent_loop.openai_turn(settings), limits or agent_loop.Limits(), on_step
        )
        production.ended(result)
        content = production.content
        status = target.done(subject.kind, content)
    except Exception as error:  # noqa: BLE001 - any failure is recorded on the item for the staff screen
        log.warning("produce failed", subject_id=str(subject_id), kind=subject.kind, error=str(error))
        content, status = with_error(production.content, "produce", error), target.failed
    await save(content, status)
