"""Storage for sitting templates. Every method takes the organisation first, so none crosses orgs."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sittings.models import SittingTemplate


async def list_for_org(session: AsyncSession, org_id: uuid.UUID) -> list[SittingTemplate]:
    """The organisation's templates, alphabetical regardless of case."""
    rows = await session.execute(
        select(SittingTemplate)
        .where(SittingTemplate.org_id == org_id)
        .order_by(func.lower(SittingTemplate.name))
    )
    return list(rows.scalars())


async def find(session: AsyncSession, org_id: uuid.UUID, template_id: uuid.UUID) -> SittingTemplate | None:
    """One template of this organisation, or nothing when it belongs to another."""
    return (
        await session.execute(
            select(SittingTemplate).where(SittingTemplate.id == template_id, SittingTemplate.org_id == org_id)
        )
    ).scalar_one_or_none()


async def name_in_use(
    session: AsyncSession, org_id: uuid.UUID, name: str, *, besides: uuid.UUID | None
) -> bool:
    """Whether another template here already has this name, ignoring case."""
    stmt = select(SittingTemplate.id).where(
        SittingTemplate.org_id == org_id, func.lower(SittingTemplate.name) == name.lower()
    )
    if besides is not None:
        stmt = stmt.where(SittingTemplate.id != besides)
    return (await session.execute(stmt)).first() is not None


async def add(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    name: str,
    config: dict[str, Any],
    created_by: uuid.UUID | None,
) -> SittingTemplate:
    """Write a new template and return it with its defaults."""
    row = SittingTemplate(org_id=org_id, name=name, config=config, created_by=created_by)
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def rename(session: AsyncSession, row: SittingTemplate, name: str) -> SittingTemplate:
    """Give a template a new name."""
    row.name = name
    await session.flush()
    await session.refresh(row)
    return row


async def remove(session: AsyncSession, org_id: uuid.UUID, template_id: uuid.UUID) -> None:
    """Drop one template of this organisation."""
    await session.execute(
        delete(SittingTemplate).where(SittingTemplate.id == template_id, SittingTemplate.org_id == org_id)
    )
