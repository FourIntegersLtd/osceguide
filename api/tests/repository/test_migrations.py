"""Alembic ran, recorded itself, and each test starts from a clean transaction."""

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.db

ROOT = Path(__file__).resolve().parents[2]


def head_revisions() -> set[str]:
    """Revision ids with nothing pointing at them — what `upgrade head` reaches."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    return set(ScriptDirectory.from_config(cfg).get_heads())


async def test_the_database_is_stamped_at_head(db_session: AsyncSession) -> None:
    stamped = {row[0] for row in (await db_session.execute(text("select version_num from alembic_version")))}
    heads = head_revisions()
    assert stamped == heads, (
        "The test database is not at head. A migration was added without the session "
        "fixture re-running, or two heads exist and need a merge revision. "
        f"stamped={sorted(stamped)} heads={sorted(heads)}"
    )


async def test_job_queue_tables_exist(db_session: AsyncSession) -> None:
    row = (await db_session.execute(text("select to_regclass('procrastinate_jobs')"))).scalar_one()
    assert row == "procrastinate_jobs"


async def test_each_test_starts_from_a_clean_transaction(db_session: AsyncSession) -> None:
    await db_session.execute(text("create temporary table scratch (n int)"))
    await db_session.execute(text("insert into scratch values (1)"))
    count = (await db_session.execute(text("select count(*) from scratch"))).scalar_one()
    assert count == 1


async def test_models_and_schema_do_not_drift(db_session: AsyncSession) -> None:
    """Autogenerate finds nothing to do against a migrated database.

    This is the guarantee ADR 0013 bought: a mapped column with no migration,
    or a migration no model reflects, fails here rather than in production.
    It also pins the procrastinate filter in `core/db.py` — without it
    autogenerate proposes dropping the job queue's tables, because they are
    applied as raw SQL and never enter Base.metadata.
    """
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from app.core.db import AUTOGENERATE_FILTERS, Base, import_all_models

    import_all_models()
    connection = await db_session.connection()

    def diff(sync_conn: object) -> list[object]:
        context = MigrationContext.configure(sync_conn, opts=dict(AUTOGENERATE_FILTERS))  # type: ignore[arg-type]
        return compare_metadata(context, Base.metadata)

    assert await connection.run_sync(diff) == []
