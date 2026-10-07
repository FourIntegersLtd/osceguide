"""A station's revisions: adding, editing, publishing, archiving, deleting.

`service.py` is about the station itself — its title, exam, current revision; this is about the
immutable revisions underneath it, where the publishing lifecycle lives.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.errors import Forbidden, raise_mapped
from app.core.tenancy import admin_org_ids
from app.features.stations import domain, errors, repository
from app.features.stations.models import StationVersion
from app.features.stations.refusals import REFUSALS as _REFUSALS
from app.features.stations.schemas import StationVersionRead
from app.features.stations.service import read_station
from app.features.stations.service_facts import refuse_while_produced
from app.features.tutor_memory import jobs as tutor_jobs

# What a candidate is shown before the station starts. Presentation rather than
# assessed content, which is why T5 lets it be corrected on a published
# version — see `domain.ensure_brief_editable`.
BRIEF_KEY = "reading_brief"


async def add_version(
    session: AsyncSession, org_id: uuid.UUID | None, station_id: uuid.UUID
) -> StationVersionRead:
    """Open a new draft, seeded from the latest published version."""
    await read_station(session, org_id, station_id)
    existing = await repository.versions_for_station(session, org_id, station_id)
    refs = [
        domain.VersionRef(number=version.version, status=domain.Status(version.status))
        for version in existing
    ]
    try:
        domain.ensure_no_open_draft(refs)
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    seed = domain.seed_version(refs)
    content: dict[str, Any] = {}
    if seed is not None:
        source = next(version for version in existing if version.version == seed.number)
        content = dict(source.content)
    station_version = await repository.add_version(
        session,
        org_id,
        station_id=station_id,
        version=domain.next_version_number(refs),
        content=content,
    )
    return _version_read(station_version)


async def edit_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    station_id: uuid.UUID,
    version: int,
    *,
    content: dict[str, Any],
    facts: dict[str, Any] | None = None,
    title: str | None = None,
) -> StationVersionRead:
    """Overwrite a draft version's content, and with it the rulings on its fact check and the
    station's title if given."""
    station_version = await _version(session, org_id, station_id, version)
    try:
        domain.ensure_editable(
            domain.VersionRef(number=station_version.version, status=domain.Status(station_version.status))
        )
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    refuse_while_produced(station_version.review)
    if title is not None:
        await repository.set_station_title(session, org_id, station_id, title=title)
    await repository.set_version_content(session, org_id, station_version.id, content=content)
    if facts is not None:
        await repository.set_version_review(
            session, station_version.id, {**(station_version.review or {}), "facts": facts}
        )
    return _version_read(await _version(session, org_id, station_id, version))


async def publish_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    station_id: uuid.UUID,
    version: int,
    *,
    actor_id: uuid.UUID,
    now: datetime,
) -> StationVersionRead:
    """Publish a draft version. A station's patient material must never reach a trainee before their
    attempt, so this is also what makes the version schedulable in a circuit.
    """
    station_version = await _version(session, org_id, station_id, version)
    try:
        new_status = domain.publish(
            domain.VersionRef(number=station_version.version, status=domain.Status(station_version.status))
        )
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.set_version_status(
        session, org_id, station_version.id, status=str(new_status), at=now, by=actor_id
    )
    # The station points at its newest published version, so a circuit can
    # reference the station and still get a frozen revision.
    await repository.set_current_version(session, org_id, station_id, version_id=station_version.id)
    await _refresh_tutor_material(session, org_id)
    return _version_read(await _version(session, org_id, station_id, version))


async def archive_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    station_id: uuid.UUID,
    version: int,
    *,
    actor_id: uuid.UUID,
    now: datetime,
) -> StationVersionRead:
    """Retire a published version so it can no longer be scheduled."""
    station_version = await _version(session, org_id, station_id, version)
    try:
        new_status = domain.archive(
            domain.VersionRef(number=station_version.version, status=domain.Status(station_version.status))
        )
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    await _refuse_while_in_use(session, station_version.id)
    await repository.set_version_status(
        session, org_id, station_version.id, status=str(new_status), at=now, by=actor_id
    )
    await _repoint_after_archiving(session, org_id, station_id, archived_version_id=station_version.id)
    await _refresh_tutor_material(session, org_id)
    return _version_read(await _version(session, org_id, station_id, version))


async def _refuse_while_in_use(session: AsyncSession, version_id: uuid.UUID) -> None:
    """A version a circuit still has to run, or a practice set holds, is not withdrawn from under it.

    Both pin this exact version, so archiving it would leave the slot or the set entry refused
    `station_not_published` the moment somebody opens it. Finished circuits do not count: their
    history keeps reading an archived version.
    """
    counts = await _use_counts(session, [version_id], open_circuits_only=True)
    circuits = counts["circuits"].get(version_id, 0)
    sets = counts["sets"].get(version_id, 0)
    if circuits or sets:
        raise errors.NotArchivableError(
            "This version is on a circuit that has not finished or in a practice set. "
            "Take it off first, or publish a new version and move them across.",
            details={"reason": "in_use", "circuits": circuits, "sets": sets},
        )


async def _refresh_tutor_material(session: AsyncSession, org_id: uuid.UUID | None) -> None:
    """Have the tutor's index catch up with a library station that was published or archived.

    Only the library is indexed, so an organisation's own station queues nothing. Without
    this the tutor quoted the old management plan, or an archived one, until the night.
    """
    if org_id is None:
        await tutor_jobs.queue_reindex(session)


async def _repoint_after_archiving(
    session: AsyncSession, org_id: uuid.UUID | None, station_id: uuid.UUID, *, archived_version_id: uuid.UUID
) -> None:
    """Keep the station's own status in step with the version just archived.

    The library and circuits list a station by its own `status` and hand out its
    `current_version_id`. Left alone, archiving the current version kept the
    station listed as published and pointing at the archived version, so every
    attempt started from it was refused `station_not_published`. The station
    falls back to its newest remaining published version, or is archived itself
    when none is left.
    """
    station = await repository.station_by_id(session, org_id, station_id)
    if station is None or station.current_version_id != archived_version_id:
        # An older version was archived; the one in use is untouched.
        return
    still_published = [
        station_version
        for station_version in await repository.versions_for_station(session, org_id, station_id)
        if station_version.status == str(domain.Status.PUBLISHED)
    ]
    if still_published:
        # `versions_for_station` is oldest first, so the last is the newest.
        await repository.set_current_version(session, org_id, station_id, version_id=still_published[-1].id)
    else:
        await repository.retire_station(session, org_id, station_id)


async def _version(
    session: AsyncSession, org_id: uuid.UUID | None, station_id: uuid.UUID, version: int
) -> StationVersion:
    """One numbered version of this org's station, or refuse if there is no such version."""
    await read_station(session, org_id, station_id)
    station_version = await repository.version_by_number(session, org_id, station_id, version)
    if station_version is None:
        raise errors.VersionNotFound()
    return station_version


async def version_history(
    session: AsyncSession, station_id: uuid.UUID, *, caller: Principal
) -> list[StationVersionRead]:
    """Every revision this station has had, newest first. An author's read.

    A history asked for by station id has no org slug to carry, so the owner is read off the station
    and matched against the caller's own memberships: a platform admin sees any station's, an
    organisation's admin sees its own. A trainee of the same organisation is refused, because this
    lists every version's whole document — the patient's persona and the examiner's material included,
    even for withdrawn revisions.
    """
    found = await repository.station_with_versions(session, station_id)
    if found is None:
        raise errors.StationNotFound()
    station, versions = found
    if not caller.is_platform_admin and (
        station.org_id is None or station.org_id not in admin_org_ids(caller)
    ):
        raise Forbidden()
    used_by = await used_by_counts(session, [station_version.id for station_version in versions])
    return [
        _version_read(station_version).model_copy(
            update={"used_by_count": used_by.get(station_version.id, 0)}
        )
        for station_version in reversed(versions)
    ]


async def used_by_counts(session: AsyncSession, station_version_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """How many things name each station version, summed across the slices
    that hold one: circuits, attempts, peer practice sessions and practice sets.

    Information for the author, not a refusal: deleting is still decided by
    status alone (T6). Imported inside because every one of those slices reads
    stations at module load.
    """
    counts = await _use_counts(session, station_version_ids)
    totals: dict[uuid.UUID, int] = dict.fromkeys(station_version_ids, 0)
    for per_slice in counts.values():
        for version_id, count in per_slice.items():
            totals[version_id] = totals.get(version_id, 0) + count
    return totals


async def _use_counts(
    session: AsyncSession, station_version_ids: list[uuid.UUID], *, open_circuits_only: bool = False
) -> dict[str, dict[uuid.UUID, int]]:
    """Per slice, how many things name each station version. The one place the four lookups live.

    Imported inside because every one of those slices reads stations at module load.
    """
    from app.features.attempts import service as attempts
    from app.features.peer_practice import service as peer_practice
    from app.features.sittings import service as sittings
    from app.features.station_sets import service as station_sets

    return {
        "circuits": await sittings.circuit_counts_by_station_version(
            session, station_version_ids, open_only=open_circuits_only
        ),
        "attempts": await attempts.attempt_counts_by_station_version(session, station_version_ids),
        "peer_sessions": await peer_practice.session_counts_by_station_version(session, station_version_ids),
        "sets": await station_sets.set_counts_by_station_version(session, station_version_ids),
    }


def _version_read(station_version: StationVersion) -> StationVersionRead:
    """Map a station version onto the schema."""
    return StationVersionRead(
        id=station_version.id,
        station_id=station_version.station_id,
        version=station_version.version,
        status=station_version.status,
        content=dict(station_version.content),
        published_at=station_version.published_at,
        archived_at=station_version.archived_at,
    )


async def delete_version(
    session: AsyncSession, org_id: uuid.UUID | None, station_id: uuid.UUID, version: int
) -> None:
    """Throw away a draft (T6).

    Only a draft: a published revision is what somebody's attempt was assessed against, and an
    archived one is how that attempt is still readable.
    """
    station_version = await _version(session, org_id, station_id, version)
    try:
        domain.ensure_deletable(
            domain.VersionRef(number=station_version.version, status=domain.Status(station_version.status))
        )
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.delete_version(session, org_id, station_version.id)
    # A station with no version left is nothing to open or publish: it goes with its last draft.
    # Only drafts can be deleted, so a station emptied this way was never published and no
    # circuit, template or attempt can refer to it; that is the check delete_station relies on.
    if not await repository.versions_for_station(session, org_id, station_id):
        await repository.delete_station(session, org_id, station_id)


async def edit_brief(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    station_id: uuid.UUID,
    version: int,
    *,
    brief: str,
) -> StationVersionRead:
    """Correct the reading brief without cutting a new version (T5).

    The documented exception to "published content is immutable": a typo in the brief should not
    require a new revision and a fresh publish. An archived version is still refused.
    """
    station_version = await _version(session, org_id, station_id, version)
    try:
        domain.ensure_brief_editable(
            domain.VersionRef(number=station_version.version, status=domain.Status(station_version.status))
        )
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)

    content = dict(station_version.content or {})
    content[BRIEF_KEY] = brief
    await repository.set_version_content(session, org_id, station_version.id, content=content)
    return _version_read(await _version(session, org_id, station_id, version))
