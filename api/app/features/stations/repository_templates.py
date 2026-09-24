"""Storage for station templates: the shapes a station may be written to.

Split from `repository.py` along the aggregate. Every function takes `org_id`
first, and `None` means the platform's own. Which ownership predicate each uses
is the tenancy decision: `owned_by` for a write, `visible_to` for a read that
should also see the platform's templates — an institution may write a station
against a platform template, and often should.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ownership import owned_by, owner_kind_for, visible_to
from app.features.stations.models import StationTemplate, StationTemplateVersion


async def create_template(
    session: AsyncSession, org_id: uuid.UUID | None, *, exam_id: uuid.UUID | None, title: str
) -> StationTemplate:
    row = StationTemplate(owner_kind=owner_kind_for(org_id), org_id=org_id, exam_id=exam_id, title=title)
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def template_by_id(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID
) -> StationTemplate | None:
    stmt = select(StationTemplate).where(owned_by(StationTemplate, org_id), StationTemplate.id == template_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def templates_visible_to(session: AsyncSession, org_id: uuid.UUID | None) -> list[StationTemplate]:
    """This owner's templates and the platform's: what a station may be built on."""
    stmt = (
        select(StationTemplate)
        .where(visible_to(StationTemplate, org_id))
        .order_by(StationTemplate.created_at, StationTemplate.id)
    )
    return list((await session.execute(stmt)).scalars())


async def template_versions(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID
) -> list[StationTemplateVersion]:
    stmt = (
        select(StationTemplateVersion)
        .where(
            owned_by(StationTemplateVersion, org_id),
            StationTemplateVersion.template_id == template_id,
        )
        .order_by(StationTemplateVersion.version)
    )
    return list((await session.execute(stmt)).scalars())


async def bindable_template_version(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> StationTemplateVersion | None:
    """A version this owner may build a station on, the platform's included."""
    """One of this org's template versions, scoped to it."""
    stmt = select(StationTemplateVersion).where(
        visible_to(StationTemplateVersion, org_id), StationTemplateVersion.id == version_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def add_template_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    template_id: uuid.UUID,
    version: int,
    structure: dict[str, Any],
) -> StationTemplateVersion:
    row = StationTemplateVersion(
        owner_kind=owner_kind_for(org_id),
        org_id=org_id,
        template_id=template_id,
        version=version,
        structure=structure,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def set_template_title(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID, *, title: str
) -> None:
    await session.execute(
        update(StationTemplate)
        .where(owned_by(StationTemplate, org_id), StationTemplate.id == template_id)
        .values(title=title)
    )


async def set_template_version_structure(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID, *, structure: dict[str, Any]
) -> None:
    await session.execute(
        update(StationTemplateVersion)
        .where(owned_by(StationTemplateVersion, org_id), StationTemplateVersion.id == version_id)
        .values(structure=structure)
    )


async def delete_template_version(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> None:
    await session.execute(
        delete(StationTemplateVersion).where(
            owned_by(StationTemplateVersion, org_id), StationTemplateVersion.id == version_id
        )
    )


async def delete_template(session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID) -> None:
    await session.execute(
        delete(StationTemplate).where(owned_by(StationTemplate, org_id), StationTemplate.id == template_id)
    )


async def set_template_version_status(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    version_id: uuid.UUID,
    *,
    status: str,
    at: datetime,
    by: uuid.UUID | None,
) -> None:
    values: dict[str, Any] = {"status": status}
    if status == "published":
        values.update(published_at=at, published_by=by)
    elif status == "archived":
        values.update(archived_at=at, archived_by=by)
    await session.execute(
        update(StationTemplateVersion)
        .where(owned_by(StationTemplateVersion, org_id), StationTemplateVersion.id == version_id)
        .values(**values)
    )


async def structure_for_version(session: AsyncSession, version_id: uuid.UUID) -> dict[str, Any] | None:
    """The block definitions a station version was written against.

    Deliberately not org-scoped, and named so. A station already resolved for
    an attempt was reached through its own tenancy check; refusing to read the
    template behind it would only mean rendering it as though it had none,
    which is a worse failure than the one this would be guarding against.
    """
    stmt = select(StationTemplateVersion.structure).where(StationTemplateVersion.id == version_id)
    row = (await session.execute(stmt)).scalar_one_or_none()
    return dict(row) if isinstance(row, dict) else None
