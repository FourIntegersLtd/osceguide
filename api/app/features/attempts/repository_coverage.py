import uuid
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models_coverage import AttemptLiveCoverage


async def read(session: AsyncSession, attempt_id: uuid.UUID) -> dict[str, Any] | None:
    row = await session.get(AttemptLiveCoverage, attempt_id)
    return row.snapshot if row else None


async def save(session: AsyncSession, attempt_id: uuid.UUID, snapshot: dict[str, Any]) -> None:
    stmt = insert(AttemptLiveCoverage).values(attempt_id=attempt_id, snapshot=snapshot)
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=[AttemptLiveCoverage.attempt_id],
            set_={"snapshot": stmt.excluded.snapshot},
        )
    )
