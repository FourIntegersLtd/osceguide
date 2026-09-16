# 0003. Postgres through SQLAlchemy and Alembic; tenancy enforced in code, not RLS

Date: 2026-09-15
Status: superseded by 0008 (SQLAlchemy and Alembic dropped; Postgres, direct access and tenancy rules stand)

## Context
Firestore forced client-side joins, unbounded arrays on the user document and non-transactional read-modify-write of progress. The b2b Supabase client spoke to Postgres over PostgREST, which meant no multi-statement transactions, foreign keys left unenforced, and migrations pasted into a web editor with no record of what ran where. Supabase row-level security was nominally enabled but the service-role key bypassed it.

## Decision
Postgres (Supabase-hosted) accessed directly with SQLAlchemy 2.0 async on the psycopg 3 driver. Schema changes are Alembic migrations run by CI and on deploy. Every org-scoped table carries an `org_id` foreign key and every org-scoped repository method takes `org_id` as its first parameter; tests prove isolation. RLS is not relied on.

## Consequences
- Real transactions: a request is one unit of work, committed by the session dependency.
- Referential integrity moves from Python checks into the database.
- Engineers must learn SQLAlchemy's declarative models and Alembic autogenerate, and review generated migrations.
- Switching hosts away from Supabase requires nothing but a new `DATABASE_URL`.
