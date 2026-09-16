"""The migration runner and the transaction wiring behave as documented."""

import psycopg
import pytest

from app.core.db import Connection
from app.core.migrations import apply_migrations, migration_files

pytestmark = pytest.mark.db


def test_migrations_are_recorded_and_idempotent(migrated_database: str) -> None:
    assert apply_migrations(migrated_database) == []  # second run applies nothing
    with psycopg.connect(migrated_database) as conn:
        versions = [r[0] for r in conn.execute("select version from supabase_migrations.schema_migrations")]
    assert versions == [p.stem.partition("_")[0] for p in migration_files()]


async def test_job_queue_tables_exist(db_conn: Connection) -> None:
    row = await (await db_conn.execute("select to_regclass('procrastinate_jobs') as t")).fetchone()
    assert row is not None and row["t"] == "procrastinate_jobs"


async def test_each_test_starts_from_a_clean_transaction(db_conn: Connection) -> None:
    await db_conn.execute("create temporary table scratch (n int)")
    await db_conn.execute("insert into scratch values (1)")
    row = await (await db_conn.execute("select count(*) as c from scratch")).fetchone()
    assert row is not None and row["c"] == 1
