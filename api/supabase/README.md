# Schema and migrations

Postgres owns the schema. Every change is a file in `migrations/`, named `<UTC timestamp>_<name>.sql`, applied in order and recorded in `supabase_migrations.schema_migrations`. That table is the answer to "which version is production on?".

## Making a change

```bash
make new-migration M=add_exams        # creates migrations/20260915120000_add_exams.sql
# write the SQL: create table, alter table, create index, create function ...
make migrate                          # applies pending files to DATABASE_URL (local)
make test                             # tests migrate a fresh database from scratch
```

Rules for the SQL you write:

- uuid primary keys with `default gen_random_uuid()`.
- Every relationship is a real foreign key. Lists of ids are join tables, never arrays or JSON.
- Org-scoped tables carry `org_id uuid not null references organizations(id)`.
- `not null` unless a value is genuinely optional; `check` constraints for enumerations.
- JSONB only for document-shaped data (a frozen engine definition, a rendered payload).
- Additive and reversible where possible. Never edit a migration that has been pushed; write a new one.

## Deploying a change

Staging and production are migrated with the Supabase CLI, which reads the same folder:

```bash
brew install supabase/tap/supabase    # once
supabase login                         # once
supabase link --project-ref <ref>      # once per environment
supabase db push                       # applies pending migrations, records them
```

The SQL editor in the Supabase dashboard is fine for exploring. If you change the schema there, capture it into a file before anyone else depends on it:

```bash
supabase db diff -f capture_hotfix     # writes the difference as a new migration
```

## Local stack

Tests and `make start` use a plain Postgres (docker compose, port 5433). The full Supabase local stack (`supabase start`) is not required.
