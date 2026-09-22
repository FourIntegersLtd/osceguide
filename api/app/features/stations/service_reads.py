"""Bulk answers about stations, for the screens that show many at once.

Split from `service.py` by concept rather than by line count: everything here
answers "tell me about these stations" for a caller that already holds a set of
ids — a console listing a circuit's slots, a dashboard counting a library. The
use cases in `service.py` act on one station at a time and enforce its
lifecycle; nothing here changes anything.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import service as catalog
from app.features.entitlements import service_access
from app.features.stations import repository, repository_library
from app.features.stations.schemas import LibraryStationRead


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
    rows = await repository_library.versions_with_stations(session, org_id, list(version_ids))
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
        for version, station in rows
    }


async def count_stations(session: AsyncSession, org_id: uuid.UUID | None) -> int:
    """How many stations this organisation has authored."""
    return await repository.count_for_org(session, org_id)


async def published_library_version_ids(
    session: AsyncSession, *, exam_id: uuid.UUID | None = None
) -> list[uuid.UUID]:
    """Version ids of every published platform-library station."""
    from app.features.stations import repository_library

    return [v.id for v, _ in await repository_library.published_library_versions(session, exam_id=exam_id)]


async def browse_library(
    session: AsyncSession,
    *,
    exam_code: str | None,
    limit: int,
    cursor: dict[str, Any] | None,
    user_id: uuid.UUID | None = None,
    now: datetime | None = None,
    all_exams: bool = False,
) -> tuple[list[LibraryStationRead], str | None]:
    """The published platform library, scoped to the exams the caller may open.

    The `owner_kind = 'platform'` half of the table had no reader at all: a
    consumer could build a practice set only out of station version ids they
    had no way to discover. An unpublished station is not in the library, and
    neither is any organisation's own — those are behind the org routes.

    It answered with every exam's stations at once, which is what put an "all
    exams" filter on a screen in a product where somebody holds one exam. A
    named `exam_code` must be one the caller may open; without one they get
    theirs. `all_exams` is the staff console, which curates the whole
    catalogue and passes it explicitly rather than by omission.
    """
    exam_id = None
    if exam_code is not None:
        if user_id is not None and now is not None and not all_exams:
            await service_access.require_exam_access(session, user_id, exam_code=exam_code, now=now)
        exam_id = (await catalog.resolve_exam(session, exam_code)).id
    elif user_id is not None and now is not None and not all_exams:
        # No exam named: theirs, rather than everybody's.
        access = await service_access.exam_access_for(session, user_id, now=now)
        if access.current is None:
            # Nothing they may open, so nothing to browse. An empty page rather
            # than a refusal: a brand-new account with no exam chosen is not an
            # error, it just has no library yet.
            return [], None
        exam_id = (await catalog.resolve_exam(session, access.current)).id

    rows, next_cursor = await repository.list_platform_library(
        session, limit=limit, cursor=cursor, exam_id=exam_id
    )
    version_ids = [row.current_version_id for row in rows if row.current_version_id is not None]
    versions = await summaries_by_version_id(session, None, version_ids)
    codes = await catalog.exam_codes_by_id(session, [row.exam_id for row in rows])

    out: list[LibraryStationRead] = []
    for row in rows:
        version = versions.get(row.current_version_id) if row.current_version_id else None
        # A published station with no current version is a seeding fault, not
        # something a browser can act on: there is nothing for it to bind.
        if version is None:
            continue
        out.append(
            LibraryStationRead(
                id=row.id,
                title=row.title,
                exam_code=codes.get(row.exam_id, ""),
                version_id=version.version_id,
                version=version.version,
                published_at=version.published_at,
            )
        )
    return out, next_cursor


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


# What a doctor is shown *after* a consultation, and nothing else. The rest of
# a station — the patient's persona, their hidden history, the examiner's
# expected answers — is what the station assesses, and putting it anywhere a
# doctor can ask for it is handing over the answers before they sit it.
#
# The management plan is already doctor-facing: it is the screen they read in
# the debrief, and `learning_events.ref_kind` counts `management_plan` as a
# thing they view. That is why this read exists here rather than in the tutor's
# slice — which blocks of a station a doctor may read is this slice's rule, and
# a reader that helped itself to `content` would be deciding it for itself.
DOCTOR_FACING_KEYS = ("management_plan", "doctor_information")

# A block the template marks `examiner` holds the expected answers. Templated
# stations therefore contribute nothing here until a template can mark a block
# as reading material; `docs/OPEN-QUESTIONS.md` T-2 is that question.


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
    out: list[MaterialSource] = []
    for version, station in await repository_library.published_library_versions(session, exam_id=exam_id):
        text = _doctor_facing_text(dict(version.content or {}))
        if not text:
            continue
        out.append(
            MaterialSource(version_id=version.id, exam_id=station.exam_id, title=station.title, text=text)
        )
    return out


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
        out: list[str] = []
        for key, inner in value.items():
            label = str(key).replace("_", " ").strip()
            texts = _flatten(inner)
            if texts:
                out.append(f"{label.capitalize()} {' '.join(texts)}")
        return out
    if isinstance(value, Sequence):
        return [text for item in value for text in _flatten(item)]
    return [str(value).strip()]
