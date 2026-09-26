"""Storage for rubrics and their versions.

Every method takes `org_id` first, and `None` means the platform's own rows.
Which of the two ownership predicates it uses is the whole of the tenancy
decision here: `owned_by` for anything that writes, `visible_to` for a read
that should also see the platform library. See `app.core.ownership`.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ownership import owned_by, owner_kind_for, visible_to
from app.core.pagination import keyset_page
from app.features.rubrics.models import Rubric, RubricVersion


async def create_rubric(session: AsyncSession, org_id: uuid.UUID | None, *, title: str) -> Rubric:
    """Insert a new, versionless rubric row. The first version is added separately."""
    rubric = Rubric(owner_kind=owner_kind_for(org_id), org_id=org_id, title=title)
    session.add(rubric)
    await session.flush()
    await session.refresh(rubric)
    return rubric


async def rubric_by_id(
    session: AsyncSession, org_id: uuid.UUID | None, rubric_id: uuid.UUID
) -> Rubric | None:
    """The owner's own rubric. Not the library: this backs edits."""
    stmt = select(Rubric).where(owned_by(Rubric, org_id), Rubric.id == rubric_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def readable_rubric(
    session: AsyncSession, org_id: uuid.UUID | None, rubric_id: uuid.UUID
) -> Rubric | None:
    """The owner's own rubric or a platform one, for reading."""
    stmt = select(Rubric).where(visible_to(Rubric, org_id), Rubric.id == rubric_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_rubrics(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
) -> tuple[list[Rubric], str | None]:
    """An org sees its own rubrics and the platform's; the platform sees its own."""
    stmt = select(Rubric).where(visible_to(Rubric, org_id))
    return await _rubric_page(session, stmt, limit=limit, cursor=cursor)


async def _rubric_page(
    session: AsyncSession, stmt: Select[Any], *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[Rubric], str | None]:
    """Shared paging for any already-filtered rubric query."""
    return await keyset_page(
        session,
        stmt,
        sort_col=Rubric.created_at,
        id_col=Rubric.id,
        limit=limit,
        cursor=cursor,
        descending=False,
    )


async def add_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    rubric_id: uuid.UUID,
    version: int,
    structure: dict[str, Any],
    system_prompt: str,
    pacing: dict[str, Any],
    result_schema_override: dict[str, Any] | None = None,
    marking_layout: dict[str, Any] | None = None,
) -> RubricVersion:
    """Insert a new version row, as a draft, under an existing rubric."""
    version_row = RubricVersion(
        rubric_id=rubric_id,
        org_id=org_id,
        version=version,
        structure=structure,
        system_prompt=system_prompt,
        pacing=pacing,
        result_schema_override=result_schema_override,
        marking_layout=marking_layout,
    )
    session.add(version_row)
    await session.flush()
    await session.refresh(version_row)
    return version_row


async def versions_for_rubric(
    session: AsyncSession, org_id: uuid.UUID | None, rubric_id: uuid.UUID
) -> Sequence[RubricVersion]:
    """Every version of this rubric the caller may read, oldest first."""
    stmt = (
        select(RubricVersion)
        .where(visible_to(RubricVersion, org_id), RubricVersion.rubric_id == rubric_id)
        .order_by(RubricVersion.version)
    )
    return (await session.execute(stmt)).scalars().all()


async def version_by_number(
    session: AsyncSession, org_id: uuid.UUID | None, rubric_id: uuid.UUID, version: int
) -> RubricVersion | None:
    """One version by its number, only for the owner writing it."""
    stmt = select(RubricVersion).where(
        owned_by(RubricVersion, org_id),
        RubricVersion.rubric_id == rubric_id,
        RubricVersion.version == version,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def version_by_id(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> RubricVersion | None:
    """A version this owner may read, which includes the platform's."""
    stmt = select(RubricVersion).where(visible_to(RubricVersion, org_id), RubricVersion.id == version_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def published_platform_version(session: AsyncSession, version_id: uuid.UUID) -> RubricVersion | None:
    """A published version of a platform rubric. Deliberately not org-scoped.

    What an exam is allowed to be marked with: an exam belongs to everyone, so
    it cannot be bound to one organisation's private rubric.
    """
    stmt = select(RubricVersion).where(
        RubricVersion.id == version_id,
        RubricVersion.org_id.is_(None),
        RubricVersion.status == "published",
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def set_version_body(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    version_id: uuid.UUID,
    *,
    structure: dict[str, Any],
    system_prompt: str,
    pacing: dict[str, Any],
    result_schema_override: dict[str, Any] | None,
    marking_layout: dict[str, Any] | None,
) -> None:
    """Overwrite a draft version's whole body in place."""
    await session.execute(
        update(RubricVersion)
        .where(owned_by(RubricVersion, org_id), RubricVersion.id == version_id)
        .values(
            structure=structure,
            system_prompt=system_prompt,
            pacing=pacing,
            result_schema_override=result_schema_override,
            marking_layout=marking_layout,
        )
    )


async def set_version_status(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    version_id: uuid.UUID,
    *,
    status: str,
    at: datetime,
    by: uuid.UUID | None,
) -> None:
    """Move a version to a new lifecycle status, stamping who did it and when."""
    column_values: dict[str, Any] = {"status": status}
    if status == "published":
        column_values |= {"published_at": at, "published_by": by}
    elif status == "archived":
        column_values |= {"archived_at": at, "archived_by": by}
    await session.execute(
        update(RubricVersion)
        .where(owned_by(RubricVersion, org_id), RubricVersion.id == version_id)
        .values(**column_values)
    )


async def set_current_version(
    session: AsyncSession, org_id: uuid.UUID | None, rubric_id: uuid.UUID, *, version_id: uuid.UUID
) -> None:
    """Point the rubric at the version new attempts should be marked against."""
    await session.execute(
        update(Rubric)
        .where(owned_by(Rubric, org_id), Rubric.id == rubric_id)
        .values(current_version_id=version_id)
    )
