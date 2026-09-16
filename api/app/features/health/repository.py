from __future__ import annotations

from app.core.db import Connection


async def ping(conn: Connection) -> None:
    await conn.execute("select 1")
