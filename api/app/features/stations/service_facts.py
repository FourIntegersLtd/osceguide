"""Checks the clinical claims in a platform station against the guidelines, as a deck's are.

Only the management plan is checked. Each of its top-level fields is a section, so a claim is
located by the field it sits in and a correction is made there. The result is kept on the
version's `review` column, never in its content, so no trainee, room or worker is served it.
Only platform stations are checked.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import publish_after_commit, user_topic
from app.core.lifecycle import Status
from app.core.logging import get_logger
from app.core.ports import GuidelineIndex, GuidelineWeb
from app.core.schemas import StationReview
from app.core.settings import Settings
from app.features.media_production import service_facts as facts_service
from app.features.stations import errors, jobs, repository, station_autogenerate
from app.features.stations import repository_templates as template_repository
from app.features.stations.models import Station, StationVersion

log = get_logger(__name__)

# Published to the admin who asked once a check settles, so the screen re-reads then.
STATION_UPDATED = "station.updated"
CHECKING = "checking"
# Kept as the review's status while the agent produces the version; nothing else may change it then.
PRODUCING = "producing"
# A field shorter than this is a name or a label, not something a guideline could contradict.
_SHORTEST_SECTION = 40
_ERROR_CHARACTERS = 300
# Only the management plan is checked. The patient's story and the doctor's notes are the scenario,
# which no guideline can contradict; checking them too cost half a run and found nothing to correct.
_CHECKED_SECTION = "management_plan"


def _text(value: object) -> str:
    """The prose under one field, flattened; links to photos and files are left out."""
    if isinstance(value, str):
        return "" if value.startswith(("http://", "https://")) else value.strip()
    if isinstance(value, dict):
        value = list(value.values())
    if isinstance(value, list):
        return "\n".join(text for text in map(_text, value) if text)
    return ""


def sections_of(content: dict[str, Any]) -> list[facts_service.Section]:
    """A station's content as sections to check: one per field with prose in it."""
    sections: list[facts_service.Section] = []
    for field, value in content.items():
        text = _text(value)
        if len(text) >= _SHORTEST_SECTION:
            place = field.replace("_", " ").strip().capitalize()
            sections.append(({"slide": None, "field": field, "place": place}, text))
    return sections


async def checked_fields(session: AsyncSession, template_version_id: uuid.UUID | None) -> frozenset[str]:
    """The block ids of the management plan in a station's template, the fields its facts are checked
    in when the station is stored flat by block id."""
    if template_version_id is None:
        return frozenset()
    template_version = await template_repository.bindable_template_version(session, None, template_version_id)
    sections = (template_version.structure or {}).get("sections") if template_version else None
    return frozenset(
        str(block.get("id"))
        for section in sections or []
        if isinstance(section, dict) and section.get("id") == _CHECKED_SECTION
        for block in section.get("blocks") or []
        if isinstance(block, dict) and block.get("id")
    )


def checked_content(content: dict[str, Any], fields: frozenset[str]) -> dict[str, Any]:
    """The part of a station's content its facts are checked in: the management plan, nested under its
    section or stored flat by block id. A station with neither is checked whole."""
    picked = {key: value for key, value in content.items() if key == _CHECKED_SECTION or key in fields}
    return picked or content


def _review_read(review: dict[str, Any] | None) -> StationReview:
    """The stored review as the screen reads it."""
    stored = review or {}
    return StationReview(
        checking=stored.get("status") == CHECKING,
        producing=stored.get("status") == PRODUCING,
        facts=stored.get("facts"),
        error=stored.get("error"),
        brief=stored.get("brief"),
        run=stored.get("run"),
    )


@dataclass(frozen=True)
class StationProduction:
    """A platform station version as the producing agent works on it. `content` is its working copy:
    the version's content with its review under `review` and the review's status under `status`, the
    shape a media item's content has."""

    version_id: uuid.UUID
    station_id: uuid.UUID
    title: str
    exam_id: uuid.UUID
    template_version_id: uuid.UUID | None
    editable: bool
    content: dict[str, Any]
    checked_fields: frozenset[str]


async def _production(
    session: AsyncSession, station_version: StationVersion, station: Station
) -> StationProduction:
    """A version and its station as the agent works on them."""
    review = dict(station_version.review or {})
    return StationProduction(
        version_id=station_version.id,
        station_id=station.id,
        title=station.title,
        exam_id=station.exam_id,
        template_version_id=station_version.template_version_id,
        editable=station_version.status == str(Status.DRAFT),
        content={**station_version.content, "review": review, "status": review.get("status")},
        checked_fields=await checked_fields(session, station_version.template_version_id),
    )


async def production_of(
    session: AsyncSession, station_id: uuid.UUID, version: int, *, lock: bool = False
) -> StationProduction:
    """A platform station version to be produced, found the way the staff screen names it; `lock`
    holds it until the transaction ends."""
    station, station_version = await _platform_version(session, station_id, version)
    if lock:
        return await production_version(session, station_version.id, lock=True)
    return await _production(session, station_version, station)


async def production_version(
    session: AsyncSession, version_id: uuid.UUID, *, lock: bool = False
) -> StationProduction:
    """A platform station version to be produced; `lock` holds it until the transaction ends."""
    found = await repository.version_with_station(session, version_id, lock=lock)
    if found is None:
        raise errors.VersionNotFound()
    return await _production(session, *found)


async def save_production(
    session: AsyncSession, version_id: uuid.UUID, working: dict[str, Any], *, requested_by: uuid.UUID
) -> None:
    """Splits a working copy back into the version's content and its review, and tells whoever asked.
    A version that is no longer a draft keeps its content: only the review is written."""
    production = await production_version(session, version_id)
    review = dict(working.get("review") or {})
    review.pop("status", None)
    if working.get("status"):
        review["status"] = working["status"]
    if production.editable:
        content = {key: value for key, value in working.items() if key not in ("review", "status")}
        await repository.set_version_content(session, None, version_id, content=content)
    await repository.set_version_review(session, version_id, review)
    publish_after_commit(
        session, user_topic(requested_by), STATION_UPDATED, {"station_id": str(production.station_id)}
    )


async def _platform_version(
    session: AsyncSession, station_id: uuid.UUID, version: int
) -> tuple[Station, StationVersion]:
    """A platform station and one of its versions; an org's station is not found here."""
    found = await repository.station_with_versions(session, station_id)
    if found is None or found[0].org_id is not None:
        raise errors.StationNotFound()
    station, versions = found
    match = next((entry for entry in versions if entry.version == version), None)
    if match is None:
        raise errors.VersionNotFound()
    return station, match


def refuse_while_produced(review: dict[str, Any] | None) -> None:
    """Refuses a change to a version the agent is producing: its next save would overwrite it."""
    if (review or {}).get("status") == PRODUCING:
        raise errors.StationBeingProduced()


async def read_review(session: AsyncSession, station_id: uuid.UUID, version: int) -> StationReview:
    """A platform station version's fact check, empty if none has run."""
    _, station_version = await _platform_version(session, station_id, version)
    return _review_read(station_version.review)


async def enqueue_check(
    session: AsyncSession, station_id: uuid.UUID, version: int, *, requested_by: uuid.UUID
) -> StationReview:
    """Starts checking a version's claims, refusing while a check of it is already running."""
    _, station_version = await _platform_version(session, station_id, version)
    review = dict(station_version.review or {})
    if review.get("status") == CHECKING:
        raise errors.FactCheckRunning()
    refuse_while_produced(review)
    review["status"] = CHECKING
    await repository.set_version_review(session, station_version.id, review)
    await jobs.enqueue_fact_check(session, version_id=station_version.id, requested_by=requested_by)
    return _review_read(review)


async def run_check(
    session: AsyncSession,
    version_id: uuid.UUID,
    *,
    requested_by: uuid.UUID,
    guidelines: GuidelineIndex | None = None,
    web: GuidelineWeb | None = None,
    complete: facts_service.Complete | None = None,
    progress: facts_service.Progress | None = None,
) -> None:
    """Checks a version's claims and keeps the result on it. A failure is kept there too, beside the
    last check that worked. The library, web search and model are the deployment's unless a test
    hands in its own."""
    [(station_version, station)] = await repository.versions_with_stations_any_owner(session, [version_id])
    review = {key: value for key, value in (station_version.review or {}).items() if key != "status"}
    try:
        review["facts"] = await facts_service.check_as_deployed(
            title=station.title,
            sections=sections_of(
                checked_content(
                    station_version.content,
                    await checked_fields(session, station_version.template_version_id),
                )
            ),
            guidelines=guidelines,
            web=web,
            complete=complete,
            on_progress=progress,
        )
        review.pop("error", None)
    except Exception as error:  # noqa: BLE001 - any failure is kept on the version for the staff screen
        log.warning("station fact check failed", version_id=str(version_id), error=str(error))
        review["error"] = {"step": "facts", "message": str(error)[:_ERROR_CHARACTERS] or type(error).__name__}
    await repository.set_version_review(session, version_id, review)
    publish_after_commit(
        session, user_topic(requested_by), STATION_UPDATED, {"station_id": str(station_version.station_id)}
    )


async def save_progress(
    session: AsyncSession, version_id: uuid.UUID, *, requested_by: uuid.UUID, facts: dict[str, Any]
) -> None:
    """Keeps a running check's claims so far on the version, still marked as checking, and tells
    whoever asked, so their screen fills in as each claim is judged."""
    [(station_version, _)] = await repository.versions_with_stations_any_owner(session, [version_id])
    await repository.set_version_review(
        session, version_id, {**(station_version.review or {}), "facts": facts}
    )
    publish_after_commit(
        session, user_topic(requested_by), STATION_UPDATED, {"station_id": str(station_version.station_id)}
    )


async def draft_production(
    session: AsyncSession, template_version_id: uuid.UUID, prompt: str, settings: Settings
) -> dict[str, Any]:
    """A fresh draft of a platform station's content from a prompt, in its template's blocks."""
    drafted = await station_autogenerate.autogenerate_station_draft(
        session, None, prompt=prompt, template_version_id=template_version_id, settings=settings
    )
    return dict(drafted["content"])
