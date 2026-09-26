"""Turning legacy station documents into platform library stations.

The consumer station library is four Firestore collections — `stations`,
`plab_stations`, `casc_stations`, `ortho_stations` — and a document in each is
already close to what `station_versions.content` holds: a name and a nested
`patient_information` block. The renderer reads the same nested shapes, which
is why it can run a migrated station at all.

So this is normalisation, not translation, and it is deliberately shallow.
The transform does not reshape clinical content, invent blocks or fill gaps:
a station that was thin in Firestore is thin here, and `scenario_is_renderable`
will say so at bootstrap by serving a degraded render it never freezes.
Rewriting content during a migration is how you discover, months later, that
the station a candidate sat is not the station anyone authored.

Every station lands **platform-owned and published**, because that is what it
already was: these are live, and an import that left them in draft would make
the whole library unrunnable on the morning of the cutover.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.migration.users import UnknownLegacyProduct, exam_for_product, parse_timestamp

__all__ = [
    "MigratedStation",
    "StationTransformError",
    "UnknownLegacyProduct",
    "station_from_document",
]

# Keys that describe the row rather than the station, and must not be carried
# into `content` — they are columns here, or they are Firestore bookkeeping.
_NOT_CONTENT = frozenset(
    {
        "id",
        "station_id",
        "app_type",
        "created_at",
        "updated_at",
        "createdAt",
        "updatedAt",
        "user_id",
        "flagged",
        "flag_count",
        "attempts",
    }
)

# The nested blocks a legacy document carries. Any of them is enough for the
# renderer to produce a real patient; none of them and there is nothing to run.
_PATIENT_BLOCKS = ("patient_information", "patient_info")


class StationTransformError(Exception):
    """A document that cannot become a station. Reported, never guessed at."""


@dataclass
class MigratedStation:
    """One library station, ready for `load_stations`."""

    legacy_id: str
    exam_code: str
    title: str
    content: dict[str, Any]
    created_at: datetime | None = None
    warnings: list[str] = field(default_factory=list)


def _title(document: dict[str, Any], legacy_id: str) -> str:
    """The station's title from whichever legacy field carries it, or a placeholder naming its id."""
    for key in ("station_name", "title", "name"):
        candidate_title = document.get(key)
        if isinstance(candidate_title, str) and candidate_title.strip():
            return candidate_title.strip()
    # Named rather than skipped: a station with no title is still a station
    # somebody wrote, and a librarian can rename it. Dropping it loses content.
    return f"Untitled station ({legacy_id})"


def station_from_document(document: dict[str, Any], *, product: str | None = None) -> MigratedStation:
    """One Firestore station document, as a platform station.

    `product` overrides the document's own `app_type`, for an export written
    one collection per file. An unknown product raises rather than defaulting
    to `sca` — the defect that had CASC stations marked with a GP rubric
    started with exactly that kind of fallback.
    """
    legacy_id = str(document.get("station_id") or document.get("id") or "").strip()
    if not legacy_id:
        raise StationTransformError("station document has no id")

    raw_product = product or document.get("app_type")
    if not raw_product:
        raise StationTransformError(f"station {legacy_id} names no product")
    exam_code = exam_for_product(str(raw_product))

    content = {key: value for key, value in document.items() if key not in _NOT_CONTENT}
    # The platform's own shape keeps the legacy id inside the content too, so a
    # rendered prompt can still be traced to the document it came from after
    # the Firestore project is archived.
    content["station_id"] = legacy_id

    warnings: list[str] = []
    if not any(isinstance(content.get(block), dict) and content[block] for block in _PATIENT_BLOCKS):
        # Imported anyway, and flagged. The bootstrap will serve a degraded
        # render and decline to freeze it, so the station is visibly broken
        # rather than silently absent from the library.
        warnings.append(f"station {legacy_id} has no patient information; it will render degraded")

    return MigratedStation(
        legacy_id=legacy_id,
        exam_code=exam_code,
        title=_title(document, legacy_id),
        content=content,
        created_at=parse_timestamp(document.get("created_at") or document.get("createdAt")),
        warnings=warnings,
    )
