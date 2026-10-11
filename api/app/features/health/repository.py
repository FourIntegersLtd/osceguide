"""The one check the health route makes of the database itself."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def ping(session: AsyncSession) -> bool:
    """Run a trivial query, so a database that cannot answer at all is caught; True once it answered."""
    await session.execute(text("select 1"))
    return True


async def unbound_platform_stations(session: AsyncSession) -> int:
    """How many published platform stations show a version with no template, so no written brief.

    Raw SQL, because this slice owns no mapping of the stations tables and reads them only to count.
    """
    result = await session.execute(
        text(
            "select count(*) from stations s "
            "join station_versions v on v.id = s.current_version_id "
            "where s.owner_kind = 'platform' and s.status = 'published' and v.template_version_id is null"
        )
    )
    return int(result.scalar_one())
