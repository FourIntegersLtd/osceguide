"""One person's station progress as the console sees it, and the two things
the old console could do to it: reset the attempt counter, and delete the
station's progress outright.

This slice is the home because the counter is its entry's, and it sits above
`attempts` (the records) and `stations` (the titles). Every write leaves an
audit row with no organisation, like every other platform act.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.attempts import service_platform_progress as attempts
from app.features.identity import service as identity
from app.features.station_sets import errors, repository
from app.features.station_sets.schemas_platform import StationProgressChange, StationProgressRead
from app.features.stations import service_platform_reads as stations
from app.features.stations.service_platform_reads import StationVersions
from app.features.tenancy import service_audit


async def station_progress(session: AsyncSession, user_id: uuid.UUID) -> list[StationProgressRead]:
    """One row per station, newest activity first: the attempts that exist
    and the counters on the person's set entries, side by side."""
    by_version = await attempts.progress_by_version(session, user_id)
    owners = await stations.owners_by_version_id(session, [row.station_version_id for row in by_version])

    rows: dict[uuid.UUID, StationProgressRead] = {}
    for progress in by_version:
        owner = owners.get(progress.station_version_id)
        if owner is None:
            continue
        current = rows.get(owner.station_id)
        newer = current is None or (
            current.last_attempt_at is not None and progress.last_attempt_at > current.last_attempt_at
        )
        rows[owner.station_id] = StationProgressRead(
            station_id=owner.station_id,
            title=owner.title,
            exam_code=owner.exam_code,
            attempts=(current.attempts if current else 0) + progress.attempts,
            evaluated=(current.evaluated if current else 0) + progress.evaluated,
            last_attempt_at=progress.last_attempt_at if newer else current.last_attempt_at,  # type: ignore[union-attr]
            last_attempt_id=progress.last_attempt_id if newer else current.last_attempt_id,  # type: ignore[union-attr]
            last_status=progress.last_status if newer else current.last_status,  # type: ignore[union-attr]
            entry_attempts=0,
        )

    entries = await repository.entries_for_owner_by_versions(session, user_id, list(owners))
    for entry in entries:
        owner = owners[entry.station_version_id]
        row = rows[owner.station_id]
        row.entry_attempts += entry.attempts
        row.set_entry_ids.append(entry.id)
    return sorted(rows.values(), key=lambda row: row.last_attempt_at or datetime.min, reverse=True)


async def _target(session: AsyncSession, user_id: uuid.UUID, station_id: uuid.UUID) -> StationVersions:
    if await identity.user_ref_by_id(session, user_id) is None:
        raise errors.UserNotFound()
    station = await stations.station_versions(session, station_id)
    if station is None:
        raise errors.StationNotFound()
    return station


async def reset_attempts(
    session: AsyncSession, user_id: uuid.UUID, station_id: uuid.UUID, *, actor: Principal
) -> StationProgressChange:
    """Zero the counters on every set entry this person holds for the station.

    Exactly what the old console did: the attempts, transcripts and marking
    stay, and the person may sit the station again against a fresh limit.
    """
    station = await _target(session, user_id, station_id)
    reset = await repository.reset_counters(session, user_id, station.version_ids)
    await service_audit.record(
        session,
        actor=actor,
        action="user.station_attempts_reset",
        target_type="user",
        target_id=str(user_id),
        summary=station.title,
        meta={"station_id": str(station_id), "entries_reset": reset},
    )
    return StationProgressChange(station_id=station_id, entries_reset=reset)


async def delete_progress(
    session: AsyncSession, user_id: uuid.UUID, station_id: uuid.UUID, *, reason: str, actor: Principal
) -> StationProgressChange:
    """Erase the station from this person's history: every attempt at it and
    what hung off them, then the entries that held it in their sets.

    The attempts go first because the entries `RESTRICT` while one points at
    them. Refused while an attempt is still running (`attempt_in_progress`).
    """
    station = await _target(session, user_id, station_id)
    deleted = await attempts.delete_progress(session, user_id, station.version_ids)
    removed = await repository.remove_entries(session, user_id, station.version_ids)
    await service_audit.record(
        session,
        actor=actor,
        action="user.station_progress_deleted",
        target_type="user",
        target_id=str(user_id),
        summary=f"{station.title}: {reason}",
        meta={
            "station_id": str(station_id),
            "reason": reason,
            "attempts_deleted": deleted,
            "entries_removed": removed,
        },
    )
    return StationProgressChange(station_id=station_id, attempts_deleted=deleted, entries_removed=removed)
