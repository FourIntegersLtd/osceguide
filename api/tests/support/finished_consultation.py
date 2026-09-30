import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import domain, repository, repository_transcript


async def finish_consultation(session: AsyncSession, attempt_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    await repository.set_status(session, attempt_id, status=domain.Status.RUNNING, at=now)
    await repository_transcript.add_chunk(
        session,
        attempt_id,
        message_id=str(uuid.uuid4()),
        seq=0,
        role="doctor",
        message="What brought you in today?",
        spoken_at=now,
    )
    await repository.set_status(session, attempt_id, status=domain.Status.INTERACTION_COMPLETE, at=now)
    await session.flush()
