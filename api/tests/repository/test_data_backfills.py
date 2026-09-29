"""The data a migration rewrites on its way up, checked row by row.

A schema change is proved by the drift test; a backfill is not, because the
test database is migrated while it is empty. Each migration that rewrites rows
keeps its SQL in a module constant, and these tests run that SQL against rows
written here, so the rule it applies is checked against the Python it mirrors.
"""

from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.db

VERSIONS = Path(__file__).resolve().parents[2] / "alembic" / "versions"


def migration(revision: str) -> ModuleType:
    """Load one migration module by its revision id; the filenames start with digits."""
    (path,) = VERSIONS.glob(f"{revision}_*.py")
    spec = importlib.util.spec_from_file_location(f"migration_{revision}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MEDIA_DOCUMENTS: list[dict[str, Any]] = [
    {"specialties": ["Cardiology", "Respiratory"], "specialty": "Respiratory"},
    {"specialties": ["  ", 7, " Renal "]},
    {"specialties": "Cardiology", "specialty": " Neurology "},
    {"specialty": "   "},
    {"specialty": 12},
    {"slides": ["Angina"]},
]


async def test_the_media_specialty_backfill_files_items_as_the_reader_does(db_session: AsyncSession) -> None:
    """The column is filled with exactly what `specialty_of` reads out of the document."""
    from app.features.media.domain import specialty_of
    from app.features.media.models import MediaItem

    items = [
        MediaItem(kind="summary", slug=f"backfill-{uuid.uuid4().hex[:8]}", title="T", content=document)
        for document in MEDIA_DOCUMENTS
    ]
    db_session.add_all(items)
    await db_session.flush()
    item_ids = [item.id for item in items]
    await db_session.execute(update(MediaItem).where(MediaItem.id.in_(item_ids)).values(specialty=None))

    await db_session.execute(text(migration("029f2c0b1966").BACKFILL_SQL))

    stored = dict(
        (
            await db_session.execute(
                select(MediaItem.id, MediaItem.specialty).where(MediaItem.id.in_(item_ids))
            )
        ).all()
    )
    assert [stored[item_id] for item_id in item_ids] == [
        specialty_of(document) for document in MEDIA_DOCUMENTS
    ]
    assert [stored[item_id] for item_id in item_ids] == ["Cardiology", "Renal", "Neurology", None, None, None]
