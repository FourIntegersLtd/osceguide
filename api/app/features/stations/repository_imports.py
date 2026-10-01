"""Storage for station imports: one row per uploaded document.

Every function that a route reaches takes `org_id` and filters with `owned_by`,
so an import is only ever read by the owner that uploaded it. `get_for_job` is
the one exception: a background job has an id and no caller, and reads the owner
off the row.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ownership import owned_by, owner_kind_for
from app.features.stations.models import StationImport


async def create_import(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    created_by: uuid.UUID,
    exam_code: str,
    original_filename: str,
    extracted_text: str,
    status: str,
    template_id: uuid.UUID | None = None,
    template_version_id: uuid.UUID | None = None,
) -> StationImport:
    """A row for one uploaded document, written before any model is asked anything."""
    station_import = StationImport(
        owner_kind=owner_kind_for(org_id),
        org_id=org_id,
        created_by=created_by,
        exam_code=exam_code,
        original_filename=original_filename,
        extracted_text=extracted_text,
        status=status,
        template_id=template_id,
        template_version_id=template_version_id,
    )
    session.add(station_import)
    await session.flush()
    await session.refresh(station_import)
    return station_import


async def import_by_id(
    session: AsyncSession, org_id: uuid.UUID | None, import_id: uuid.UUID
) -> StationImport | None:
    """One import this owner uploaded, by id."""
    stmt = select(StationImport).where(owned_by(StationImport, org_id), StationImport.id == import_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_for_job(session: AsyncSession, import_id: uuid.UUID) -> StationImport | None:
    """One import by id alone, for the background job, which reads the owner off the row."""
    stmt = select(StationImport).where(StationImport.id == import_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def recent_imports(
    session: AsyncSession, org_id: uuid.UUID | None, *, limit: int
) -> list[StationImport]:
    """This owner's imports, newest first."""
    stmt = (
        select(StationImport)
        .where(owned_by(StationImport, org_id))
        .order_by(StationImport.created_at.desc(), StationImport.id.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars())


async def save_progress(
    session: AsyncSession, station_import: StationImport, **changes: Any
) -> StationImport:
    """Write the named columns on one import and hand back the row as stored.

    Refreshed after the flush because `updated_at` is set by the database, and
    reading an expired column outside the flush raises in async SQLAlchemy.
    """
    for column, value in changes.items():
        setattr(station_import, column, value)
    await session.flush()
    await session.refresh(station_import)
    return station_import
