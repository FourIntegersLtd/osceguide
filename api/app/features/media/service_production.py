"""The body of a media item, as the AV production jobs need it."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.media import errors, repository


@dataclass(frozen=True)
class ProductionItem:
    id: uuid.UUID
    kind: str
    title: str
    content: dict[str, Any]
    exam_id: uuid.UUID | None


async def production_item(session: AsyncSession, item_id: uuid.UUID) -> ProductionItem:
    row = await repository.by_id(session, item_id)
    if row is None:
        raise errors.ItemNotFound()
    return ProductionItem(
        id=row.id,
        kind=row.kind,
        title=row.title,
        content=dict(row.content or {}),
        exam_id=row.exam_id,
    )


async def replace_content(session: AsyncSession, item_id: uuid.UUID, content: dict[str, Any]) -> None:
    await repository.update_item(session, item_id, content=content)
