"""Publishing study material queues a tutor re-index for that item alone."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import repository as identity_repo
from app.features.media import service as media
from tests.support.catalog import ensure_exam
from tests.support.fakes import FakeVectorIndex

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


async def test_publish_queues_a_material_reindex_job(db_session: AsyncSession) -> None:
    await ensure_exam(db_session, "sca")
    author = await identity_repo.create_user(
        db_session, email=f"p{uuid.uuid4().hex[:8]}@example.com", name="Author", password_hash=None
    )
    item = await media.create(
        db_session,
        kind="summary",
        title="Publish queues reindex",
        summary="A short summary.",
        content={"body": "Offer a talking therapy or a medicine."},
        exam_code="sca",
        author_id=author.id,
    )

    await media.publish(db_session, item.id, index=FakeVectorIndex(), now=NOW)
    await db_session.flush()

    rows = (
        await db_session.execute(
            text(
                "SELECT task_name, args FROM procrastinate_jobs "
                "WHERE args->>'media_item_id' = :id ORDER BY id"
            ),
            {"id": str(item.id)},
        )
    ).all()
    assert rows == [("reindex_media_item", {"media_item_id": str(item.id)})]
