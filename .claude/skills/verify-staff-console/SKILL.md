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
