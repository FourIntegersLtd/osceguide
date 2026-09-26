# platform-api deploy checklist

Use this before promoting **platform-api** to production (not b2c-api/b2b-api).
A push to `main` deploys staging by itself; production changes only through the
promote workflow (see [ENVIRONMENT.md](ENVIRONMENT.md), "Staging and production").
Each backend redeploys only for its own folder: `platform-api/**`, `b2c-api/**`
or `b2b-api/**`.

## Before deploy

1. **Migrations** — Railway runs `alembic upgrade head` before every platform-api
   deploy (`preDeployCommand` in `railway.toml`); a failed migration stops the deploy
   and the previous version keeps serving. Make sure each new migration only adds:
   a rollback keeps the new schema.
2. **Tests** — `cd platform-api && poetry run pytest -q` (or rely on CI on `main`).
3. **Staging smoke** — Sign in, start a practice attempt, confirm voice bootstrap and
   marking jobs complete on staging.
4. **`VOICE_BACKEND_LABEL`** — Do **not** change on a live environment without a
   cutover plan. Workers resolve this API by label; a mismatch orphans in-flight
   sessions. See [ENVIRONMENT.md](ENVIRONMENT.md).
5. **`LIVEKIT_AGENT_NAMESPACE`** — When sharing a LiveKit project with other
   environments, set a unique namespace locally so dev workers do not steal prod
   dispatches (see `.env.example`).

## After deploy

- Confirm `/health` reports `status: ok` and the promoted `commit`, and one
  authenticated read (`/api/v1/me`).
- Watch `GET /platform/jobs?status=failed` if staff console is wired.
- If peer-practice or coverage migrations ran, spot-check queue join and live
  coverage on staging before announcing.

## What does not deploy with this service

| Service | Trigger |
|---------|---------|
| platform-api, platform-worker | `platform-api/**`: staging on a push to `main`, production when the promote workflow moves `production` |
| b2c-api | `b2c-api/**` in backend repo |
| b2b-api | `b2b-api/**` in backend repo |
| assessment-platform workers | Push to `assessment-platform` `main` → GHCR (+ optional K8s rollout) |
