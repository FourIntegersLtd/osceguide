---
name: verify-staff-console
description: How to prove a change to the staff console and platform operations works — health and ops, background jobs, Alembic migrations, the worker entry point, domains/platform and the staff-* capabilities, and the api architecture guards. Use before calling any staff-console, migration or ops change done.
---

# Verify the staff console

Pick the **lowest level that can see your change**, run it, and report the command and its output.

| Your change | Minimum proof |
|---|---|
| A platform route or support action | Level 1, including the audit row it writes |
| A migration | Level 1 + `make data-model` + upgrade a fresh DB and an already-migrated one |
| A guard or shared `core/` infrastructure | `make guards` and `make ci` |
| A background job or the worker entry | Level 1 + run `make worker` and watch the job finish |
| A screen under `domains/platform`, `app/staff`, `staff-*` | Level 1 if the backend changed, then Level 2 |
| Ownership (a new folder or file area) | `.claude/OWNERS.md` row + `tests/guards/test_ownership.py` |

## Level 1 - backend tests (needs the docker services)

```bash
cd api
docker compose up -d            # Postgres :5433, Redis :6380; without them DB tests skip and a pass means nothing
poetry run alembic upgrade head
poetry run pytest -q tests/http/test_platform_*.py tests/http/test_health.py tests/http/test_audit_trail.py \
  tests/repository/test_health_sweep.py tests/repository/test_job_reads.py tests/unit/test_jobs_registry.py
make guards && make data-model
```

`tests/repository/test_migrations.py` and `tests/migration` run alone (they error when run after the
repository suite).

## Level 2 - the console in a browser

Seed with `poetry run python scripts/seed_platform.py`, start the api on :8002 and the web app routed
to it (never a remote api), sign in as a platform admin (`web/scripts/admin-totp.mjs` prints the MFA
code) and drive the screen with the platform-web `verify` skill. Check the audit trail shows the action.

## Traps

- A migration must only add: every deploy runs `alembic upgrade head`, and a rollback keeps the schema.
- `schema.d.ts` is one generated file: `make openapi`, then `npm run platform:types`, one session at a time.
- The ops screen's background tasks come from the jobs registry; a job not registered never runs.
- Staging gets seeded data only; `app.migration` refuses to import under `APP_ENV=staging`.
- A periodic task is not proven by its unit test: run `make worker`, defer it by hand (`poetry run procrastinate --app=app.core.jobs.app defer ...` or insert an old succeeded row in `procrastinate_jobs`) and read the `audit_log` row it wrote. For the size alarm, lower `DATABASE_SIZE_BUDGET_MB` for the run to cross 60%.
- A new table needs its `**Growth:**` line (and `**Retention:**` for per-turn/unbounded) in `DATA-MODEL.md`, or `make data-model` fails.
- Browser check of a health panel: `make start` fights anything already on :8002 (another session's stub may hold it). Run `uvicorn` on another port with `DATABASE_URL` set to the local docker DB and start web with `PLATFORM_API_URL=http://127.0.0.1:<port>`, `VERIFY_API_URL` the same. `bootstrap_admin.py` accounts need `update users set must_change_password=false` before the harness reaches `/staff`. To see a degraded size read for real, hold `lock table audit_log in access exclusive mode` in a psql session: the size query blocks and the server cancels it.

**A command-line tool that must survive Ctrl-C**: prove it against a throwaway local database (`create database …`, `alembic upgrade head`, seed with `session_replication_role = replica` to skip FKs; `attempts.kind` must be `practice` and `status` `evaluated` for the check constraints). A `kill -INT` on a shell background job does nothing, because non-interactive shells start it with SIGINT ignored; launch it from Python with `preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_DFL)`.
