"""procrastinate job queue schema

Revision ID: 0001
Revises:
Create Date: 2026-09-15
"""

from __future__ import annotations

from collections.abc import Sequence
from importlib import resources

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The job queue's tables, ship with the procrastinate package. Applying it
    # here means every environment gets the queue with the rest of the schema.
    schema_sql = resources.files("procrastinate.sql").joinpath("schema.sql").read_text()
    op.execute(schema_sql)


def downgrade() -> None:
    """Remove everything the package's schema created.

    Discovered rather than listed: procrastinate ships tables, composite types,
    enums and functions, and the set changes between releases. A hand-written
    list goes stale silently, and the symptom is a downgrade that appears to
    work followed by an upgrade that fails on "already exists".
    """
    op.execute("DROP SCHEMA IF EXISTS procrastinate CASCADE")
    op.execute(
        """
        DO $$
        DECLARE
            obj record;
        BEGIN
            FOR obj IN
                SELECT c.relname AS name
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname LIKE 'procrastinate%'
            LOOP
                EXECUTE format('DROP TABLE IF EXISTS public.%I CASCADE', obj.name);
            END LOOP;

            FOR obj IN
                SELECT p.oid::regprocedure AS signature
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'public' AND p.proname LIKE 'procrastinate%'
            LOOP
                EXECUTE format('DROP FUNCTION IF EXISTS %s CASCADE', obj.signature);
            END LOOP;

            FOR obj IN
                SELECT t.typname AS name
                FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE n.nspname = 'public' AND t.typname LIKE 'procrastinate%'
            LOOP
                EXECUTE format('DROP TYPE IF EXISTS public.%I CASCADE', obj.name);
            END LOOP;
        END;
        $$
        """
    )
