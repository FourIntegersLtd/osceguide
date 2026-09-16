"""Apply `supabase/migrations/*.sql` to a database, in order, once each.

Production and staging are migrated by the Supabase CLI (`supabase db push`),
which records applied versions in `supabase_migrations.schema_migrations`.
This runner does the same thing against a local or test database so the test
suite never needs the CLI. It writes to the same table with the same shape,
so a database migrated here and one migrated by the CLI agree on history.

Usage: `python -m app.core.migrations` (uses DATABASE_URL).
"""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg

from app.core.db import libpq_url
from app.core.settings import PROJECT_ROOT, get_settings

MIGRATIONS_DIR = PROJECT_ROOT / "supabase" / "migrations"

_BOOTSTRAP = """
create schema if not exists supabase_migrations;
create table if not exists supabase_migrations.schema_migrations (
    version text primary key,
    name text,
    statements text[]
);
"""


def migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def apply_migrations(database_url: str) -> list[str]:
    """Apply pending migrations and return the versions applied this run."""
    applied_now: list[str] = []
    with psycopg.connect(libpq_url(database_url), autocommit=True) as conn:
        conn.execute(_BOOTSTRAP)
        rows = conn.execute("select version from supabase_migrations.schema_migrations").fetchall()
        already = {row[0] for row in rows}
        for path in migration_files():
            version, _, name = path.stem.partition("_")
            if version in already:
                continue
            sql = path.read_text()
            with conn.transaction():
                conn.execute(sql)
                conn.execute(
                    "insert into supabase_migrations.schema_migrations (version, name, statements) "
                    "values (%s, %s, %s)",
                    (version, name, [sql]),
                )
            applied_now.append(version)
    return applied_now


def main() -> int:
    applied = apply_migrations(get_settings().database_url)
    if applied:
        print("applied:", ", ".join(applied))  # noqa: T201
    else:
        print("nothing to apply")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
