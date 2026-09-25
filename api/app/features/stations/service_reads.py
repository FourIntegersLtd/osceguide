"""Bulk answers about stations, for the screens that show many at once.

Everything here answers "tell me about these stations" for a caller that already holds a set of ids —
a console listing a circuit's slots, a dashboard counting a library. Nothing here changes anything.
The library's own reader — the browse page and a single station from it — is in
`service_library_reads.py`.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.stations import repository, repository_library


@dataclass(frozen=True)
class StationSummary:
    """A station version as a row on somebody else's screen."""

    version_id: uuid.UUID
    station_id: uuid.UUID
    title: str
    version: int
    status: str
    owner_kind: str
    published_at: datetime | None


async def summaries_by_version_id(
    session: AsyncSession, org_id: uuid.UUID | None, version_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, StationSummary]:
    """Titles for a set of station versions, keyed by version id.

    The frontend resolves these one id at a time against the catalogue — the
    N+1 the read models exist to delete.
    """
    pairs = await repository_library.versions_with_stations(session, org_id, list(version_ids))
    return {
        version.id: StationSummary(
            version_id=version.id,
            station_id=station.id,
            title=station.title,
            version=version.version,
            status=version.status,
            owner_kind=station.owner_kind,
            published_at=version.published_at,
        )
        for version, station in pairs
    }


async def count_stations(session: AsyncSession, org_id: uuid.UUID | None) -> int:
    """How many stations this organisation has authored."""
    return await repository.count_for_org(session, org_id)


async def count_library_stations(session: AsyncSession, exam_ids: list[uuid.UUID]) -> int:
    """How many published library stations this organisation may run as-is."""
    return await repository.count_platform_library(session, exam_ids)


async def published_library_version_ids(
    session: AsyncSession, *, exam_id: uuid.UUID | None = None
) -> list[uuid.UUID]:
    """Version ids of every published platform-library station."""
    from app.features.stations import repository_library

    return [
        version.id
        for version, _ in await repository_library.published_library_versions(session, exam_id=exam_id)
    ]


@dataclass(frozen=True)
class VersionMaterial:
    """One station version's document, for a caller that already holds the id.

    Deliberately *not* lifecycle-checked the way `runnable_station` is. That
    one answers "may this be run now", and archiving a station must not make a
    consultation somebody already sat unreadable: a candidate reads back the
    station as it was, and the version they sat is frozen on their attempt.
    """

    version_id: uuid.UUID
    station_id: uuid.UUID
    title: str
    exam_id: uuid.UUID
    content: dict[str, Any]


async def version_material(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> VersionMaterial | None:
    """The document behind a station version, scoped to who may see it."""
    found = await repository.version_for_attempt(session, org_id, version_id)
    if found is None:
        return None
    version, station = found
    return VersionMaterial(
        version_id=version.id,
        station_id=station.id,
        title=station.title,
        exam_id=station.exam_id,
        content=dict(version.content or {}),
    )


# What a doctor is shown *after* a consultation, and nothing else. The rest of a station — the
# patient's persona, hidden history, the examiner's expected answers — is what the station assesses,
# and putting it anywhere a doctor can ask for it is handing over the answers before they sit it.
DOCTOR_FACING_KEYS = ("management_plan", "doctor_information")

# A block the template marks `examiner` holds the expected answers. Templated stations therefore
# contribute nothing here until a template can mark a block as reading material (see
# `platform-web/docs/BACKLOG.md` T-2).


@dataclass(frozen=True)
class MaterialSource:
    """A published station as indexable reading material."""

    version_id: uuid.UUID
    exam_id: uuid.UUID | None
    title: str
    text: str


async def published_material(
    session: AsyncSession, *, exam_id: uuid.UUID | None = None
) -> list[MaterialSource]:
    """The doctor-facing text of every published library station.

    A station with no management plan contributes nothing rather than
    contributing its patient brief.
    """
    sources: list[MaterialSource] = []
    for version, station in await repository_library.published_library_versions(session, exam_id=exam_id):
        text = _doctor_facing_text(dict(version.content or {}))
        if not text:
            continue
        sources.append(
            MaterialSource(version_id=version.id, exam_id=station.exam_id, title=station.title, text=text)
        )
    return sources


def _doctor_facing_text(content: Mapping[str, Any]) -> str:
    """Flatten the doctor-facing blocks into one searchable string."""
    parts: list[str] = []
    for key in DOCTOR_FACING_KEYS:
        parts.extend(_flatten(content.get(key)))
    return " ".join(part for part in parts if part).strip()


def _flatten(value: Any) -> list[str]:
    """Text out of a block, whatever shape its author gave it."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()]
    if isinstance(value, Mapping):
        parts: list[str] = []
        for key, inner in value.items():
            label = str(key).replace("_", " ").strip()
            texts = _flatten(inner)
            if texts:
                parts.append(f"{label.capitalize()} {' '.join(texts)}")
        return parts
    if isinstance(value, Sequence):
        return [text for item in value for text in _flatten(item)]
    return [str(value).strip()]
