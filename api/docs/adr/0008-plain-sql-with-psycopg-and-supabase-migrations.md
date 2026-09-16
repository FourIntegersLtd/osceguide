# 0008. Plain SQL through psycopg; Supabase CLI owns migrations

Date: 2026-09-15
Status: superseded by 0013

## Context
ADR 0003 chose SQLAlchemy and Alembic. On review the user asked for the simplest design that still fixes the b2b weaknesses: real constraints, transactions for multi-step operations, real Postgres tests, a clean data-access boundary, and tracked schema changes. An ORM is a convenience, not a requirement for any of those. Two facts decided the shape: the Supabase Python client goes through PostgREST, which cannot open a multi-statement transaction or take row locks; and the job queue needs a direct Postgres connection regardless. One direct connection path is simpler than a client plus a driver.

## Decision
Repositories hold plain SQL and run it on a psycopg 3 connection from a pool. The request dependency opens one transaction per request. Postgres owns the schema: every change is a file in `supabase/migrations/` applied by the Supabase CLI in deployed environments and by `app/core/migrations.py` locally and in tests, both recording into `supabase_migrations.schema_migrations`. No ORM, no Alembic, no supabase-py.

## Consequences
- Multi-step operations and row locks (`select … for update`, `skip locked`) are ordinary Python code.
- Tests run on a plain Postgres container migrated from scratch in seconds.
- Engineers write SQL and review it; there is no autogenerate. Schema and query stay visible side by side.
- Supabase remains the host; nothing else from Supabase is a runtime dependency.
