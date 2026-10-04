"""Checks the clinical claims in a platform station against the guidelines, as a deck's are.

Each top-level field of the content is a section, so a claim is located by the field it sits in
and a correction is made there. The result is kept on the version's `review` column, never in its
content, so no trainee, room or worker is served it. Only platform stations are checked.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import publish_after_commit, user_topic
from app.core.logging import get_logger
from app.core.ports import GuidelineIndex, GuidelineWeb
from app.features.media_production import service_facts as facts_service
from app.features.stations import errors, jobs, repository
from app.features.stations.models import Station, StationVersion
from app.features.stations.schemas import StationReview

log = get_logger(__name__)

# Published to the admin who asked once a check settles, so the screen re-reads then.
STATION_UPDATED = "station.updated"
CHECKING = "checking"
# A field shorter than this is a name or a label, not something a guideline could contradict.
_SHORTEST_SECTION = 40
_ERROR_CHARACTERS = 300


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


def _review_read(review: dict[str, Any] | None) -> StationReview:
    """The stored review as the screen reads it."""
    stored = review or {}
    return StationReview(
        checking=stored.get("status") == CHECKING, facts=stored.get("facts"), error=stored.get("error")
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
            sections=sections_of(station_version.content),
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
