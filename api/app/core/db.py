"""Database access: psycopg 3, plain SQL, one transaction per request.

No ORM. Repositories hold SQL strings and run them on a connection. Postgres
owns the schema, the constraints and the foreign keys (see `supabase/`).

- `get_connection` is the FastAPI dependency. It hands the handler a
  connection already inside a transaction: commit when the handler returns,
  roll back when it raises. Services never call commit.
- Rows come back as dicts (`row_factory=dict_row`) so a repository can build
  its return type without positional indexing.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

from psycopg import AsyncConnection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.settings import get_settings

Connection = AsyncConnection[DictRow]


def libpq_url(url: str) -> str:
    """Normalise any Postgres URL to the form libpq accepts.

    Railway and Supabase hand out `postgres://`; some tools spell a driver
    (`postgresql+psycopg://`). libpq wants plain `postgresql://`.
    """
    for prefix in ("postgresql+psycopg://", "postgresql+asyncpg://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix) :]
    return url


_pool: AsyncConnectionPool | None = None


async def get_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = AsyncConnectionPool(
            conninfo=libpq_url(settings.database_url),
            min_size=1,
            max_size=settings.database_pool_size,
            kwargs={"row_factory": dict_row},
            open=False,
        )
        await _pool.open()
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
    _pool = None


async def get_connection() -> AsyncIterator[Connection]:
    """Request-scoped unit of work: commit on success, roll back on error."""
    pool = await get_pool()
    async with pool.connection() as conn, conn.transaction():
        yield cast(Connection, conn)  # rows are dicts: the pool sets row_factory=dict_row
