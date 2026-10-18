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

## What a failure looks like here
- A migration that drops or rewrites (a rollback must keep working), or that has no DATA-MODEL change.
- A staff action that is not platform-admin only or not audited.
- A guard weakened to pass instead of the code moved.
- A job not registered, or one that loops for ever on bad input.
