"""Entitlements as the people who answer support see them.

"I paid and I cannot practise" is answered from here: every grant a person
has ever held, live or not, with its source and who made it. The org and
consumer reads say what is live; support needs the history.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import service as catalog
from app.features.entitlements import errors, repository, service
from app.features.entitlements.models import Entitlement
from app.features.entitlements.schemas import PlatformEntitlementRead
from app.features.identity import service as identity


async def _require_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    if await identity.user_ref_by_id(session, user_id) is None:
        raise errors.GranteeNotFound()


async def list_for_user(
    session: AsyncSession, user_id: uuid.UUID, *, now: datetime
) -> list[PlatformEntitlementRead]:
    """Every grant this person has held, newest last, revoked ones included."""
    await _require_user(session, user_id)
    return [await _read(session, row, now=now) for row in await repository.for_user(session, user_id)]


async def _read(session: AsyncSession, row: Entitlement, *, now: datetime) -> PlatformEntitlementRead:
    code = await catalog.exam_code_by_id(session, row.exam_id)
    base = service._read(row, code or "", now=now)
    return PlatformEntitlementRead(
        **base.model_dump(), source_ref=row.source_ref, org_id=row.org_id, granted_by=row.granted_by
    )
