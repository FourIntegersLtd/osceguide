"""Every table in `public` has row level security on.

Supabase exposes `public` through its Data API to `anon` and `authenticated`. The app connects
as the owning role, which bypasses RLS (ENABLE, not FORCE), so enabling it with no policies
denies the Data API everything and costs the app nothing.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def test_every_public_table_has_row_level_security(db_session: AsyncSession) -> None:
    rows = await db_session.execute(
        text(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p') AND NOT c.relrowsecurity "
            "ORDER BY c.relname"
        )
    )
    missing = [r[0] for r in rows]
    assert not missing, (
        f"Tables without row level security: {missing}. Add "
        "`op.execute('ALTER TABLE <name> ENABLE ROW LEVEL SECURITY')` to the migration that "
        "creates the table (no policies: the app is the owner and bypasses RLS)."
    )


async def test_supabase_api_roles_can_read_no_public_table(db_session: AsyncSession) -> None:
    rows = await db_session.execute(
        text(
            "SELECT c.relname, r.rolname FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "CROSS JOIN (VALUES ('anon'), ('authenticated')) AS r(rolname) "
            "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p') "
            "AND has_table_privilege(r.rolname, c.oid, 'SELECT') ORDER BY 1, 2"
        )
    )
    readable = [tuple(r) for r in rows]
    assert not readable, f"anon/authenticated can still SELECT: {readable[:5]}"
