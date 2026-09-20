# platform-api deploy checklist

Use this before deploying the **platform-api** Railway service (not b2c-api/b2b-api).
Classic production on Railway only redeploys when `b2c-api/**` or `b2b-api/**` change;
a push that touches only `platform-api/**` does not rebuild those services.

## Before deploy

1. **Migrations** — Run Alembic against the target database in a maintenance window:
   `alembic upgrade head` (Docker/Railway start command does this on boot; confirm
   revision chain locally first).
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

- Confirm `/health` and one authenticated read (`/api/v1/me`).
- Watch `GET /platform/jobs?status=failed` if staff console is wired.
- If peer-practice or coverage migrations ran, spot-check queue join and live
  coverage on staging before announcing.

## What does not deploy with this service

| Service | Trigger |
|---------|---------|
| b2c-api | `b2c-api/**` in backend repo |
| b2b-api | `b2b-api/**` in backend repo |
| assessment-platform workers | Push to `assessment-platform` `main` → GHCR (+ optional K8s rollout) |
