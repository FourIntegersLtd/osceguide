"""Row level security on every table in `public`, with no policies.

Supabase serves `public` through its Data API to the `anon` and `authenticated` roles. The app
and worker connect as the owning role, which bypasses RLS (ENABLE, not FORCE), so they are
unaffected while the Data API sees zero rows. Where those roles exist (Supabase only) their
grants are revoked too, including the defaults for future objects. Tenancy stays in app code.
New tables must enable RLS themselves: `tests/integration/test_every_table_has_rls.py`.

Revision ID: 9b3d5e71c2a8
Revises: e82f4a6b1d57
Create Date: 2026-10-31
"""

from __future__ import annotations

from alembic import op

revision = "9b3d5e71c2a8"
down_revision = "e82f4a6b1d57"
branch_labels = None
depends_on = None

_FOR_EACH_TABLE = """
DO $$
DECLARE t record;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I {action} ROW LEVEL SECURITY', t.tablename);
  END LOOP;
END $$;
"""

_REVOKE_API_ROLES = """
DO $$
DECLARE r text;
BEGIN
  FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %I', r);
      EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM %I', r);
      EXECUTE format('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM %I', r);
      EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM %I', r);
      EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM %I', r);
      EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM %I', r);
    END IF;
  END LOOP;
END $$;
"""


def upgrade() -> None:
    op.execute(_FOR_EACH_TABLE.format(action="ENABLE"))
    op.execute(_REVOKE_API_ROLES)


def downgrade() -> None:
    # Grants are not restored: re-granting the Data API is a deliberate act.
    op.execute(_FOR_EACH_TABLE.format(action="DISABLE"))
