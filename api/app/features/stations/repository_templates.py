"""Storage for station templates: the shapes a station may be written to.

Every function takes `org_id` first, and `None` means the platform's own. Which ownership predicate
each uses is the tenancy decision: `owned_by` for a write, `visible_to` for a read that should also
see the platform's templates — an institution may write a station against a platform template, and
often should.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import delete, exists, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ownership import owned_by, owner_kind_for, visible_to
from app.core.pagination import keyset_page
from app.core.search import contains_text
from app.features.stations.models import StationTemplate, StationTemplateVersion


async def create_template(
    session: AsyncSession, org_id: uuid.UUID | None, *, exam_id: uuid.UUID | None, title: str
) -> StationTemplate:
    """Create a new template shell, with no versions yet."""
    template = StationTemplate(owner_kind=owner_kind_for(org_id), org_id=org_id, exam_id=exam_id, title=title)
    session.add(template)
    await session.flush()
    await session.refresh(template)
    return template


async def template_by_id(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID
) -> StationTemplate | None:
    """One template this org owns, by id."""
    stmt = select(StationTemplate).where(owned_by(StationTemplate, org_id), StationTemplate.id == template_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def templates_visible_to(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    search: str | None = None,
    exam_id: uuid.UUID | None = None,
    published_only: bool = False,
) -> tuple[list[StationTemplate], str | None]:
    """A page of this owner's templates and the platform's, oldest first: what a
    station may be built on.

    `search` matches a title fragment. `exam_id` narrows to templates written for that exam, plus
    every exam-agnostic template — one written with no exam at all matches any exam, the same rule
    platform-web applied client-side before this filter existed. `published_only` keeps only
    templates that have at least one published version, so a station is never built on a shape that
    is all drafts.
    """
    stmt = select(StationTemplate).where(visible_to(StationTemplate, org_id))
    if search and search.strip():
        stmt = stmt.where(contains_text(StationTemplate.title, search))
    if exam_id is not None:
        stmt = stmt.where(or_(StationTemplate.exam_id == exam_id, StationTemplate.exam_id.is_(None)))
    if published_only:
        stmt = stmt.where(
            exists().where(
                StationTemplateVersion.template_id == StationTemplate.id,
                StationTemplateVersion.status == "published",
            )
        )
    return await keyset_page(
        session,
        stmt,
        sort_col=StationTemplate.created_at,
        id_col=StationTemplate.id,
        limit=limit,
        cursor=cursor,
        descending=False,
    )


async def template_versions(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID
) -> list[StationTemplateVersion]:
    """Every version of this template, oldest first."""
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
    """Add a new draft version to a template."""
    template_version = StationTemplateVersion(
        owner_kind=owner_kind_for(org_id),
        org_id=org_id,
        template_id=template_id,
        version=version,
        structure=structure,
    )
    session.add(template_version)
    await session.flush()
    await session.refresh(template_version)
    return template_version


async def set_template_title(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID, *, title: str
) -> None:
    """Rename a template."""
    await session.execute(
        update(StationTemplate)
        .where(owned_by(StationTemplate, org_id), StationTemplate.id == template_id)
        .values(title=title)
    )


async def set_template_version_structure(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID, *, structure: dict[str, Any]
) -> None:
    """Overwrite a draft template version's structure."""
    await session.execute(
        update(StationTemplateVersion)
        .where(owned_by(StationTemplateVersion, org_id), StationTemplateVersion.id == version_id)
        .values(structure=structure)
    )


async def delete_template_version(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> None:
    """Remove a draft template version."""
    await session.execute(
        delete(StationTemplateVersion).where(
            owned_by(StationTemplateVersion, org_id), StationTemplateVersion.id == version_id
        )
    )


async def delete_template(session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID) -> None:
    """Remove a template that has no versions left."""
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
    """Move a template version to `published` or `archived`, stamping who did it and when."""
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
    structure = (await session.execute(stmt)).scalar_one_or_none()
    return dict(structure) if isinstance(structure, dict) else None
