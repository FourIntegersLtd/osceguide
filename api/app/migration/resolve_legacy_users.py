"""Map Firestore consumer user ids to platform `users.id`."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity.models import UserIdentity
from app.migration.load_legacy_b2c import LEGACY_CONSUMER_PROVIDER


async def legacy_consumer_user_ids(session: AsyncSession) -> dict[str, uuid.UUID]:
    """Every linked legacy consumer Firestore document id, mapped to its platform `users.id`."""
    identity_rows = await session.execute(
        select(UserIdentity.subject, UserIdentity.user_id).where(
            UserIdentity.provider == LEGACY_CONSUMER_PROVIDER
        )
    )
    return {str(subject): user_id for subject, user_id in identity_rows.all() if subject}
