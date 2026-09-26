"""The one check the health route makes of the database itself."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def ping(session: AsyncSession) -> None:
    """Run a trivial query, so a database that cannot answer at all is caught."""
    await session.execute(text("select 1"))
