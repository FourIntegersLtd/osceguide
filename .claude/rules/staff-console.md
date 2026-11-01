---
paths:
  - "api/app/features/health/**"
  - "api/alembic/**"
  - "api/app/worker/**"
  - "api/app/features/dashboard/{router_platform,service_console,service_platform_users}.py"
  - "api/tests/guards/**"
  - "web/src/domains/platform/**"
  - "web/src/capabilities/{staff-growth,staff-media,staff-moderation}/**"
  - "web/src/app/staff/**"
---
# Staff console, ops and migrations: what to know

Owner: `staff-console-owner`. Proof: `verify-staff-console`. Staff actions are platform-admin only
(ADR 0020, platform support actions); each one is audited.

- **A migration and `docs/DATA-MODEL.md` change in the same commit** (`make data-model`). A migration
  is ask-first. Every deploy runs `alembic upgrade head`, so a migration must only add (a rollback
  keeps the new schema). Chain on the current head; one migration per batch.
- **A migration that creates a table runs `ALTER TABLE <name> ENABLE ROW LEVEL SECURITY`** (no policies);
  `tests/integration/test_every_table_has_rls.py` enforces it.
- A push to `main` deploys staging, never production. Production moves only through "Promote api to
  production" (moves `production-api`; ask first). Real data never goes to staging.
- `make worker` runs background jobs (procrastinate, ADR 0006). `health/` is the readiness probe; the ops
  screen (`domains/platform/Ops.tsx`, `BackgroundTasks.tsx`) shows background tasks. A job registry test
  (`test_jobs_registry`) pins what is registered.
- A migrated database is empty: seed with `scripts/seed_platform.py` (`make seed-platform` is a dry
  run). Staff accounts use MFA (`admin-totp.mjs` for local sign-in).
- Guards (`api/tests/guards`) are the architecture: `core` never imports `features`, routers are
  thin, services never commit, SQL lives in repositories, every error is declared. A failing guard
  means the change is in the wrong place, not that the guard is wrong. `test_ownership.py` fails if a
  tracked source file has no owner or two: edit `.claude/OWNERS.md`.
- Three failures that are not breakage: `test_the_engine_only_needs_pydantic` fails when its file runs
  and passes by id; `test_assistant_routes`/`test_voice_routes` fail while a local `.env` sets
  `LIVEKIT_AGENT_NAMESPACE`; `tests/migration` errors after `tests/repository`, run it alone. DB tests
  silently skip without docker, and then a pass means nothing.
- Web: `domains/platform` and `app/staff` hold the console (orgs, users, billing queue, ops, audit,
  announcements, authoring, media, moderation, station flags, referral payouts). Behaviour belongs to
  the area the screen acts on; this owner owns the console shell and its support actions.
- One Poetry/npm session at a time on `openapi.json` and `schema.d.ts`: `make openapi`, then
  `npm run platform:types`.

- Guards that press a transition at once need committed data on separate sessions (`tests/support/committed_worlds.py`). `candidate_result_*` are append-only by trigger: clean up inside `append_only_triggers_off(session, tables)`, never by a bare delete.

- **The field guide is generated.** `docs/guides/platform-api-field-guide.html` has its `SCHEMA` block between `SCHEMA:BEGIN/END` markers, written by `api/scripts/build_field_guide.py` from `DATA-MODEL.md` and `Base.metadata`; a migration means rerunning it (`PYTHONPATH=. poetry run python scripts/build_field_guide.py`). `make data-model` also fails if the guide's route list differs from `api/openapi.json`.

- **`/health` has a `content` check**: `error` (status `degraded`) while a published platform station's current version has no template binding. A release never seeds templates or binds stations; run `scripts/seed_station_templates.py` then `scripts/link_stations_to_templates.py` with `--env <env> --apply`. `promote-api` Gates 3 and 6 refuse on it. A new check goes through `_answers_in_time`: a fresh log-and-carry-on handler breaks the `LOG_ONLY_HANDLERS` ceiling.

- **The console is built from the assess recipe.** Every screen opens with `B2CPageHeader` (there is no console header; `consoleDesign.test.ts` fails on a screen without it or with its own `<h1>`), at most one `B2CHero` directly under it, lists of records are `Table themeType="b2b"` with `empty` and `more={pages}`, tiles are `StatGrid`/`StatTile` (the assess stat card, also used by `OrgDashboard` and `Results`), and `Panel` is for forms and settings only. `web` tests are `node:test` files: run them with `npm test`, not vitest.
- **Every table declares its growth.** Each `### table` section in `api/docs/DATA-MODEL.md` opens with `**Growth:** fixed | per-user | per-org | per-attempt | per-turn | unbounded.`; a `per-turn` or `unbounded` table must add `**Retention:** <the job or rule that prunes or compacts it>`. `scripts/check_data_model.py` (in `make arch`) fails on a missing class or a vague retention. A table with truly no retention writes `Retention: GAP: ...` and is listed in `KNOWN_GAPS` (ceiling only shrinks): that list is the standing audit of what will fill the database next. New table: declare growth in the same commit as the migration.
- **Database size is watched, not hoped for.** `GET /platform/health` carries `database_size`, measured live by `health.service_size` (no worker needed). The daily `record_database_size` task stores a reading in `database_size_readings` and writes one `database.size_warning` (60% of `DATABASE_SIZE_BUDGET_MB`) or `database.size_critical` (80%, plus Sentry) audit row per crossing, using the stored `alert_level`, not per run. `prune_job_history` runs procrastinate's `delete_old_jobs` (`JOB_HISTORY_RETENTION_DAYS`); events cascade, failed jobs stay. A periodic task that must not fail silently uses `_run_recorded` (writes `sweep.failed`) and goes in `STATE` in `test_jobs_fail_visibly` with a forcing test, not in `NO_OWN_STATE`.

- **The size alarm's three rules.** The health size read is limited by the server (`statement_timeout` inside a savepoint), never by cancelling the query: an asyncio cancel mid-query on the request's shared session breaks every later statement. `record_database_size` returns the Sentry sentence and `run_size_check` sends it after the commit (a page from inside is sent again when a failed commit is retried). The compare-then-write takes `pg_advisory_xact_lock` first (`tests/integration/test_database_size_race.py`). `FactList` truncates values: a sentence goes in its own paragraph.
- **Never re-chain a migration that has already been applied anywhere.** `alembic_version` holds one
  pointer, so moving a migration's `down_revision` makes alembic treat every newly inserted ancestor
  as already run: `upgrade head` reports nothing to do and the columns never appear. It bit production
  on 2026-10-31 (the RLS migration had been applied by hand before the transcript and size migrations
  were chained in front of it). Before editing any `down_revision`, run `alembic current` against every
  deployed database, not just a local one. Repair is `alembic stamp <the real parent>` then
  `alembic upgrade head`; it only works because these migrations' `upgrade()` are idempotent or fail
  loudly. No guard catches this: the file was untracked, so nothing could compare it against `main`.
- **`VACUUM` needs a session or direct connection**, never Supabase's `:6543` transaction pooler. Plain `VACUUM` returns only the heap tail; indexes keep their size until `VACUUM FULL`.

## What a failure looks like here
- A migration that drops or rewrites (a rollback must keep working), or that has no DATA-MODEL change.
- A staff action that is not platform-admin only or not audited.
- A guard weakened to pass instead of the code moved.
- A job not registered, or one that loops for ever on bad input.
- A green `Promote api to production` is not a deploy: Railway production needs a human approval per service (platform-api and platform-worker; `railway api 'mutation { deploymentApprove(id: ...) }'`). Read `/health` after any promote.
