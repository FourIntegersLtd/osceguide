"""Copying legacy mocks into station sets, the "My sessions" list.

A legacy mock is a user's named bundle of stations (`name`, `created_by`, `stations`, each with
how often it was run). It becomes one `StationSet` with one `StationSetEntry` per station that
exists in the library. A slot's id is built from the station's ORIGINAL position in the legacy
list (`_mock_slots`), not its position after skipping missing stations, so importing a missing
station later can never shift another slot's id. The attempts inside a mock are copied by the
`attempts` step; `link_attempts_to_sessions` then hangs each one on its station slot, so a
session's review shows the transcript and feedback. The set also carries the run counts the mock
stored. Not copied: `duration` and `available_slots` (no column; both were booking-UI fields).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import Attempt
from app.features.station_sets.models import StationSet, StationSetEntry
from app.migration.attempts import attempt_from_transcript
from app.migration.b2c_lookups import Lookups, StepReport
from app.migration.legacy_ids import legacy_row_id
from app.migration.load_attempts import legacy_ref_for
from app.migration.users import UnknownLegacyProduct, exam_for_product, parse_timestamp

_NAME_LIMIT = 200


def _count(raw: object) -> int:
    """A stored run count as a non-negative integer; anything unreadable is zero."""
    try:
        return max(int(raw or 0), 0)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return 0


def _mock_slots(
    document: dict[str, Any], exam_code: str, lookups: Lookups
) -> list[tuple[int, dict[str, Any], uuid.UUID]]:
    """Every in-library station in a mock, with its ORIGINAL legacy list index.

    The index comes from `enumerate` over the raw list, before any station missing from the
    library is skipped, so a slot's id and position never shift when a missing station is
    imported later and the mock is re-read.
    """
    slots: list[tuple[int, dict[str, Any], uuid.UUID]] = []
    for index, station in enumerate(document.get("stations") or []):
        if not isinstance(station, dict):
            continue
        version_id = lookups.station_version(exam_code, station.get("station_id"))
        if version_id is None:
            continue
        slots.append((index, station, version_id))
    return slots


async def load_mocks(
    session: AsyncSession, documents: Sequence[dict[str, Any]], lookups: Lookups
) -> StepReport:
    """Load each legacy mock as a station set owned by its creator; skip unknown owners and stations."""
    report = StepReport()
    for document in documents:
        mock_id = str(document.get("mock_id") or document.get("id") or "").strip()
        owner_id = lookups.user(document.get("created_by") or document.get("user_id"))
        try:
            exam_code = exam_for_product(str(document.get("app_type") or "sca"))
        except UnknownLegacyProduct:
            report.problem(f"Mock {mock_id}: unknown product {document.get('app_type')!r}.")
            continue
        exam_id = lookups.exams.get(exam_code)
        if not mock_id or owner_id is None or exam_id is None:
            report.count("mocks skipped (owner or exam not imported)")
            continue
        raw_stations = [station for station in document.get("stations") or [] if isinstance(station, dict)]
        missing = sum(
            1
            for station in raw_stations
            if lookups.station_version(exam_code, station.get("station_id")) is None
        )
        report.count("mock stations not in the library (left out)", missing)
        slots = _mock_slots(document, exam_code, lookups)
        if not slots:
            report.count("mocks skipped (no station in the library)")
            continue
        set_id = legacy_row_id(f"{exam_code}:mock:{mock_id}")
        if await session.get(StationSet, set_id) is None:
            created = parse_timestamp(document.get("created_at"))
            session.add(
                StationSet(
                    id=set_id,
                    owner_user_id=owner_id,
                    exam_id=exam_id,
                    name=str(document.get("name") or "Session").strip()[:_NAME_LIMIT] or "Session",
                    locked=document.get("locked") is True,
                    completed_at=created if document.get("completed") is True else None,
                    **({"created_at": created} if created else {}),
                )
            )
            report.count("sessions created")
        else:
            report.count("sessions already there")
        for index, station, version_id in slots:
            entry_id = legacy_row_id(f"{exam_code}:mock:{mock_id}:{index}")
            if await session.get(StationSetEntry, entry_id) is not None:
                continue
            session.add(
                StationSetEntry(
                    id=entry_id,
                    set_id=set_id,
                    position=index,
                    station_version_id=version_id,
                    attempts=_count(station.get("attempts")),
                    debrief_attempts=_count(station.get("debrief_attempts")),
                )
            )
            report.count("session stations created")
    await session.flush()
    return report


def _entry_ids_by_station(
    documents: Sequence[dict[str, Any]], lookups: Lookups
) -> dict[tuple[str, str, str], uuid.UUID]:
    """Map (exam, mock id, station id) to the id `load_mocks` gave that station slot.

    Uses the same original-index slots as `load_mocks`, so the id always matches.
    """
    found: dict[tuple[str, str, str], uuid.UUID] = {}
    for document in documents:
        mock_id = str(document.get("mock_id") or document.get("id") or "").strip()
        try:
            exam_code = exam_for_product(str(document.get("app_type") or "sca"))
        except UnknownLegacyProduct:
            continue
        for index, station, _version_id in _mock_slots(document, exam_code, lookups):
            station_id = str(station.get("station_id") or "")
            found.setdefault(
                (exam_code, mock_id, station_id), legacy_row_id(f"{exam_code}:mock:{mock_id}:{index}")
            )
    return found


async def link_attempts_to_sessions(
    session: AsyncSession,
    mocks: Sequence[dict[str, Any]],
    transcripts: Sequence[dict[str, Any]],
    lookups: Lookups,
) -> StepReport:
    """Hang each imported practice attempt on the session station it was run from.

    An attempt becomes a `set_station` attempt on its slot when its transcript names a mock and a
    station that the session import created. Idempotent: only attempts still `practice` are touched.
    """
    report = StepReport()
    entries = _entry_ids_by_station(mocks, lookups)
    wanted = list(set(entries.values()))
    known_entries = set(
        (await session.scalars(select(StationSetEntry.id).where(StationSetEntry.id.in_(wanted)))).all()
    )
    for document in transcripts:
        app_type = str(document.get("app_type") or "sca")
        mock_id = str(document.get("mock_id") or "").strip()
        if not mock_id:
            continue
        try:
            exam_code = exam_for_product(app_type)
        except UnknownLegacyProduct:
            continue
        entry_id = entries.get((exam_code, mock_id, str(document.get("station_id") or "")))
        if entry_id is None or entry_id not in known_entries:
            report.count("attempts in a mock with no session station")
            continue
        reference = legacy_ref_for(attempt_from_transcript(document, app_type=app_type))
        if not reference:
            continue
        result = await session.execute(
            update(Attempt)
            .where(Attempt.legacy_ref == reference, Attempt.kind == "practice")
            .values(kind="set_station", set_entry_id=entry_id)
        )
        report.count("attempts linked to their session", result.rowcount or 0)
    await session.execute(
        update(StationSetEntry)
        .where(
            StationSetEntry.last_attempt_at.is_(None),
            StationSetEntry.id.in_(
                select(Attempt.set_entry_id)
                .where(Attempt.set_entry_id.is_not(None), Attempt.kind == "set_station")
                .distinct()
            ),
        )
        .values(
            last_attempt_at=(
                select(func.max(Attempt.created_at))
                .where(Attempt.set_entry_id == StationSetEntry.id)
                .scalar_subquery()
            )
        )
    )
    await session.flush()
    return report
