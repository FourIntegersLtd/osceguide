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
    seed = domain.seed_version(refs)
    content: dict[str, Any] = {}
    if seed is not None:
        source = next(version for version in existing if version.version == seed.number)
        content = dict(source.content)
    version_row = await repository.add_version(
        session,
        org_id,
        station_id=station_id,
        version=domain.next_version_number(refs),
        content=content,
    )
    return _version_read(version_row)


async def edit_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    station_id: uuid.UUID,
    version: int,
    *,
    content: dict[str, Any],
) -> StationVersionRead:
    version_row = await _version(session, org_id, station_id, version)
    try:
        domain.ensure_editable(
            domain.VersionRef(number=version_row.version, status=domain.Status(version_row.status))
        )
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.set_version_content(session, org_id, version_row.id, content=content)
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
    version_row = await _version(session, org_id, station_id, version)
    try:
        new_status = domain.publish(
            domain.VersionRef(number=version_row.version, status=domain.Status(version_row.status))
        )
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.set_version_status(
        session, org_id, version_row.id, status=str(new_status), at=now, by=actor_id
    )
    # The station points at its newest published version, so a circuit can
    # reference the station and still get a frozen revision.
    await repository.set_current_version(session, org_id, station_id, version_id=version_row.id)
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
    version_row = await _version(session, org_id, station_id, version)
    try:
        new_status = domain.archive(
            domain.VersionRef(number=version_row.version, status=domain.Status(version_row.status))
        )
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.set_version_status(
        session, org_id, version_row.id, status=str(new_status), at=now, by=actor_id
    )
    return _version_read(await _version(session, org_id, station_id, version))


async def _version(
    session: AsyncSession, org_id: uuid.UUID | None, station_id: uuid.UUID, version: int
) -> StationVersion:
    await read_station(session, org_id, station_id)
    version_row = await repository.version_by_number(session, org_id, station_id, version)
    if version_row is None:
        raise errors.VersionNotFound()
    return version_row


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
    return [_version_read(version_row) for version_row in reversed(versions)]


def _version_read(version_row: StationVersion) -> StationVersionRead:
    return StationVersionRead(
        id=version_row.id,
        station_id=version_row.station_id,
        version=version_row.version,
        status=version_row.status,
        content=dict(version_row.content),
        published_at=version_row.published_at,
        archived_at=version_row.archived_at,
    )


async def delete_version(
    session: AsyncSession, org_id: uuid.UUID | None, station_id: uuid.UUID, version: int
) -> None:
    """Throw away a draft (T6).

    Only a draft: a published revision is what somebody's attempt was assessed against, and an
    archived one is how that attempt is still readable.
    """
    version_row = await _version(session, org_id, station_id, version)
    try:
        domain.ensure_deletable(
            domain.VersionRef(number=version_row.version, status=domain.Status(version_row.status))
        )
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.delete_version(session, org_id, version_row.id)


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
    version_row = await _version(session, org_id, station_id, version)
    try:
        domain.ensure_brief_editable(
            domain.VersionRef(number=version_row.version, status=domain.Status(version_row.status))
        )
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)

    content = dict(version_row.content or {})
    content[BRIEF_KEY] = brief
    await repository.set_version_content(session, org_id, version_row.id, content=content)
    return _version_read(await _version(session, org_id, station_id, version))
