"""Storage for SCIM provisioning: the connector's tokens, and a roster read by offset.

SCIM pages by `startIndex`, not by cursor, and needs the total; that is the one
roster read not served by `repository.list_trainees`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.roster.models import ScimToken, Trainee


async def create_token(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    token_hash: str,
    token_prefix: str,
    label: str,
    created_by: uuid.UUID | None,
) -> ScimToken:
    """Store a new token's hash and return the row."""
    token = ScimToken(
        org_id=org_id, token_hash=token_hash, token_prefix=token_prefix, label=label, created_by=created_by
    )
    session.add(token)
    await session.flush()
    await session.refresh(token)
    return token


async def live_token_by_hash(session: AsyncSession, org_id: uuid.UUID, token_hash: str) -> ScimToken | None:
    """This organisation's unrevoked token with this hash, or None."""
    stmt = select(ScimToken).where(
        ScimToken.org_id == org_id, ScimToken.token_hash == token_hash, ScimToken.revoked_at.is_(None)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def tokens_for(session: AsyncSession, org_id: uuid.UUID) -> list[ScimToken]:
    """Every token this organisation has issued, newest first, revoked ones included."""
    stmt = select(ScimToken).where(ScimToken.org_id == org_id).order_by(ScimToken.created_at.desc())
    return list((await session.execute(stmt)).scalars())


async def mark_used(session: AsyncSession, org_id: uuid.UUID, token_id: uuid.UUID, *, at: datetime) -> None:
    """Record that a token was just used, so a stale connector is visible."""
    await session.execute(
        update(ScimToken).where(ScimToken.org_id == org_id, ScimToken.id == token_id).values(last_used_at=at)
    )


async def revoke_token(
    session: AsyncSession, org_id: uuid.UUID, token_id: uuid.UUID, *, at: datetime
) -> bool:
    """Revoke one of this organisation's tokens; False if it has none by that id."""
    result = await session.execute(
        update(ScimToken)
        .where(ScimToken.org_id == org_id, ScimToken.id == token_id)
        .values(revoked_at=func.coalesce(ScimToken.revoked_at, at))
        .returning(ScimToken.id)
    )
    return result.scalar_one_or_none() is not None


async def trainees_page(
    session: AsyncSession, org_id: uuid.UUID, *, email: str | None, offset: int, limit: int
) -> tuple[list[Trainee], int]:
    """A page of this organisation's roster by offset, oldest first, with the total.

    `email` narrows to one address, which is how a connector asks whether
    somebody is already there before it creates them.
    """
    stmt = select(Trainee).where(Trainee.org_id == org_id)
    total_stmt = select(func.count(Trainee.id)).where(Trainee.org_id == org_id)
    if email is not None:
        stmt = stmt.where(Trainee.email == email)
        total_stmt = total_stmt.where(Trainee.email == email)
    total = int((await session.execute(total_stmt)).scalar_one())
    page = await session.execute(stmt.order_by(Trainee.created_at, Trainee.id).offset(offset).limit(limit))
    return list(page.scalars()), total


async def trainee_fresh(session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID) -> Trainee | None:
    """A trainee re-read from the database, not the session's copy.

    A SCIM write answers with the resource as it now stands, `lastModified`
    included, which an `UPDATE` just changed in Postgres and left expired here.
    """
    stmt = (
        select(Trainee)
        .where(Trainee.org_id == org_id, Trainee.id == trainee_id)
        .execution_options(populate_existing=True)
    )
    return (await session.execute(stmt)).scalar_one_or_none()
