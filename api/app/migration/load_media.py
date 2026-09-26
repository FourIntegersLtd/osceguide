"""Loading consumer study material into `media_items`.

Idempotent on `content->>'legacy_ref'`, which the transform always writes.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog.models import Exam
from app.features.media.models import MediaItem
from app.migration.media import MigratedMedia
from app.migration.report import LoadReport


async def _existing_by_legacy_ref(session: AsyncSession) -> dict[str, uuid.UUID]:
    existing_rows = await session.execute(
        select(MediaItem.content["legacy_ref"].astext, MediaItem.id).where(
            MediaItem.content["legacy_ref"].astext.isnot(None)
        )
    )
    return {str(legacy): item_id for legacy, item_id in existing_rows.all() if legacy}


async def load_media(
    session: AsyncSession,
    migrated_items: Sequence[MigratedMedia],
    *,
    now: datetime | None = None,
) -> LoadReport:
    """Load study material. Skips rows whose `legacy_ref` is already present."""
    report = LoadReport()
    at = now or datetime.now(UTC)

    exam_rows = await session.execute(select(Exam.code, Exam.id))
    exams = {str(code).lower(): exam_id for code, exam_id in exam_rows.all()}
    by_legacy_ref = await _existing_by_legacy_ref(session)

    for migrated_item in migrated_items:
        if migrated_item.legacy_ref in by_legacy_ref:
            report.media_existing += 1
            if migrated_item.kind == "podcast":
                report.podcasts_existing += 1
            continue

        exam_id = exams.get(migrated_item.exam_code)
        if exam_id is None:
            report.problem(
                f"media {migrated_item.legacy_ref}: exam {migrated_item.exam_code!r} is not in this "
                "database; run alembic upgrade head so consumer exams exist"
            )
            continue

        media_item = MediaItem(
            kind=migrated_item.kind,
            slug=migrated_item.slug,
            title=migrated_item.title,
            summary=migrated_item.summary,
            content=migrated_item.content,
            exam_id=exam_id,
            author_id=None,
            status="published",
            published_at=migrated_item.published_at or at,
        )
        session.add(media_item)
        await session.flush()

        by_legacy_ref[migrated_item.legacy_ref] = media_item.id
        report.media_created += 1
        if migrated_item.kind == "podcast":
            report.podcasts_created += 1

    return report
