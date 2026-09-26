# Environment and secrets

Every setting is read once into one `Settings` object (`app/core/settings.py`) from the
environment and, locally, `.env`.

The design principle worth knowing before the table: **secrets have no defaults outside
local and test.** A model validator refuses to start a staging or production process
with any of the ten required values missing, which is how the "worker guard fails open"
class of bug is prevented — a missing `WORKER_SECRET` cannot silently become an
unauthenticated worker route.

Published version: https://claude.ai/artifact/DdGp1umMckFMvBiiMaLPWQ

## Required when deployed

Staging and production refuse to boot without all ten. `JWT_SECRET` must also be at
least 32 characters.

| Variable | Default | What it does, and what breaks without it |
|---|---|---|
| `DATABASE_URL` | local postgres | Any Postgres URL form is normalised to async psycopg. Locally `postgres:postgres@localhost:5432/osce_platform`. |
| `JWT_SECRET` | dev-only value | Signs access tokens. Local and test get a fixed development value that could never be mistaken for a production one. |
| `WORKER_SECRET` | — | The shared secret on every `/api/worker` route, sent as `X-Worker-Secret`. *The reason the whole no-defaults rule exists.* |
| `CORS_ORIGINS` | localhost:3000 | Comma-separated. Production origins are configuration, not code: a deploy that forgot this once accepted credentialed requests from localhost, and staging accepted production's origin. |
| `LIVEKIT_URL` | — | Without it, `voice-token` raises `VoiceUnavailable` rather than issuing a token that goes nowhere. |
| `LIVEKIT_API_KEY` | — | Token signing for rooms. |
| `LIVEKIT_API_SECRET` | — | As above. |
| `STRIPE_WEBHOOK_SECRET` | — | Per endpoint. Without it webhooks are refused, not trusted — a missing value loses purchases rather than granting them falsely. |
| `RESEND_API_KEY` | — | The only email configuration there is. |
| `OPENAI_API_KEY` | — | Primary marking model. Jobs fail and retry without it; transcripts are kept. |

## Everything else

| Variable | Default | Notes |
|---|---|---|
| `APP_ENV` | local | local · test · staging · production. Selects whether secrets are required and whether logs are JSON. |
| `DATABASE_POOL_SIZE` / `_ECHO` | 10 / false | Connection pool and SQL echo. |
| `REDIS_URL` / `REDIS_DISABLED` | localhost:6379/0 / false | Cloud slot counting, and the fan-out behind the live streams (ADR 0015). The app runs without it, but with more than one API replica a stream is then only told about writes its own replica handled — set it in any deployment that scales past one. |
| `JWT_ISSUER` / `_ACCESS_TTL_SECONDS` / `_REFRESH_TTL_SECONDS` | osce-guide / 15 min / 30 days | Access tokens are short; the refresh chain carries the session. |
| `STREAM_TICKET_TTL_SECONDS` | 60 | How long a stream ticket may be redeemed for. It is spent the instant it is minted; a minute is for a slow network, not for keeping. |
| `LIVEKIT_ROUTING_MODE` | self-hosted | `self-hosted` or `livekit-cloud`. Only ever downgrades at runtime, never up. |
| `VOICE_BACKEND_LABEL` | platform | The key the worker looks this API up by in its own `VOICE_BACKENDS_JSON`, so all three backends coexist under different labels during the cutover. **Changing this orphans in-flight sessions.** |
| `LIVEKIT_TOKEN_TTL_SECONDS` | 3600 | Room token lifetime. |
| `LIVEKIT_CLOUD_OVERFLOW_ENABLED` / `_MAX_CONCURRENT` | false / 20 | *Defaults match the legacy backends exactly*, because the Redis key is shared with them during coexistence — if these disagree, two backends disagree about how full Cloud is. |
| `LIVEKIT_CLOUD_SLOT_PENDING_TTL_SECONDS` / `_SLOT_TTL_SECONDS` | 300 / 2100 | How long a reservation is held before a worker connects, and for a whole session after. |
| `EMAIL_FROM` | OSCE Guide \<noreply@…\> | Envelope sender. |
| `STRIPE_SECRET_KEY` | — | Checkout. **Not** in the required ten, so a deploy can boot without being able to sell. |
| `CLERK_SECRET_KEY` / `CLERK_PUBLISHABLE_KEY` | — | Partner SSO, brokered through Clerk. **Not** in the required ten: a deploy without them simply cannot offer SSO, and `POST /auth/sso/login` and `/callback` refuse with `sso_login_unavailable` rather than trusting an unverified token. The organisation's `issuer` carries its Clerk frontend domain. |
| `MARKING_PRIMARY_MODEL` / `_EFFORT` | gpt-5-mini / low | Effort is set *explicitly* because unset means "medium" under any gpt-5 model — a cost decision nobody made. |
| `MARKING_FALLBACK_MODEL` / `ANTHROPIC_API_KEY` | claude-sonnet-4-5 | Fallback marking. |
| `WORKER_CONCURRENCY` | 4 | Background job parallelism. |
| `FRONTEND_URL` / `LOG_LEVEL` | localhost:3000 / INFO | Link building and logging. Logs become JSON automatically when deployed. |
| `RAILWAY_GIT_COMMIT_SHA` | — | Set by Railway on every deploy, never by hand. `/health` reports it as `commit`, so anyone can see what staging or production runs; the promote workflow refuses a commit staging is not running. |
| `SENTRY_DSN` | — | Error reporting, off unless set. Traces are sampled at 5% because an API the console polls would otherwise bill for its own heartbeat, and the request body is never sent — it holds passwords, legacy tokens and transcripts. |
| `CARTESIA_API_KEY` | — | TTS for slide and podcast production. Jobs raise `av_unavailable` without it. |
| `AWS_REGION` / `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_S3_BUCKET` | — | Where produced audio and video are stored. Jobs raise `av_unavailable` without a bucket. |
| `MEDIA_AV_FONT_DIR` | — | Optional extra font directory for slide video. Empty uses the bundled fonts. |

## Local gotcha

A populated local `.env` has been observed breaking tests in the legacy `b2b-api` —
worker-secret and LiveKit values leak into the test run and five tests fail. Those
failures are environmental, not regressions. Check what your `.env` is injecting before
chasing a red suite.

## Building the image

`ENGINE_REPO_TOKEN` is not a runtime setting: it is a **build** argument, and
the only thing it does is let `poetry install` read the private repository the
marking engine lives in. Pass it to `docker build --build-arg`, and set the
same value as the `ENGINE_REPO_TOKEN` secret in GitHub Actions. Make it
read-only, scoped to `OSCEGuide-assessment-platform`, and give it an expiry.
On Railway it is simply a service variable: Railway passes service variables
to the build as build arguments. The Dockerfile declares it only in its
throwaway `dependencies` stage, so the shipped image's `docker history` never
shows it. Railway's builder does not support BuildKit secret mounts
(`--mount=type=secret`); every build failed while the Dockerfile used one.

The build ends with `python -c "import osce_assessment"`. That line is not
decoration. `poetry install` prints "Installing osce-assessment" and exits
zero even when the clone produced nothing, so without the check an image with
no marking engine builds green, starts, answers its health check, serves every
page and refuses the one thing it exists to do.

## Staging and production

Two Railway environments in the "OSCE Guide server backend" project, each with
its own platform-api, platform-worker, Postgres (`platform-postgres`, our
pgvector image in `infra/postgres/`) and Redis. Nothing is shared between them.

| | Staging | Production |
|---|---|---|
| Deploys from | `main`, by itself after every push | `production`, moved only by the promote workflow |
| `APP_ENV` | `staging` | `production` |
| Data | Seeded test data only (`scripts/seed_platform.py`) | Real people |
| LiveKit project | `new-test-agent` | the production project |
| Stripe | test-mode keys and webhook | live keys and webhook |
| `JWT_SECRET`, `WORKER_SECRET` | its own | its own, never copied to staging |

**Getting a change to production.** Merge to `main`; CI runs and Railway deploys
staging. Test it there. Then GitHub → Actions → "Promote platform-api to
production" → Run workflow. It checks the commit is on `main`, CI passed, staging
runs it and is healthy, and a test account can sign in on staging and read its
dashboard; then it fast-forwards `production`, and Railway deploys it. `/health`
on either environment reports the commit it runs.

**Rolling back.** Railway → production → platform-api → Deployments → the
previous deployment → Redeploy (about two minutes). Do the same for
platform-worker. A rollback puts old code back but never undoes a migration.

**Migrations only add.** Every deploy runs `alembic upgrade head` before traffic
moves (platform-api's pre-deploy command; the worker has none, so two migrators
never race). Because a rollback keeps the new schema,
old code must still run on it: add columns and tables freely, and drop or rename
one only in a later release, after no deployed code uses it.

**Real data never reaches staging.** Every copy script imports `app.migration`,
and that package refuses to load under `APP_ENV=staging`. Staging's database is
reachable only from inside Railway's staging environment, where `APP_ENV` is
always `staging`.

### Railway service settings

These live in the Railway dashboard (service → Settings), not in a file. Railway
ignores `railway.toml` for services that never used Config as Code, and Config as
Code ends on 2026-12-01. Set them the same way in both environments; only the
branch differs.

| Setting | platform-api | platform-worker |
|---|---|---|
| Source → Branch | `main` on staging, `production` on production | same |
| Source → Root directory | `/platform-api` | `/platform-api` |
| Build → Builder / Dockerfile path | Dockerfile, `/platform-api/Dockerfile` | same |
| Build → Watch paths | `/platform-api/**` | `/platform-api/**` |
| Deploy → Custom start command | empty (the Dockerfile's `uvicorn`) | `python -m app.worker.main` |
| Deploy → Pre-deploy command | `alembic upgrade head` | empty, so two migrators never race |
| Deploy → Healthcheck path | `/health` | empty (the worker serves no HTTP) |

Railway runs the pre-deploy command in its own step, and its output is not in the
deploy log. After a deploy with a migration, check that the worker's jobs succeed
and `/health` reports the new commit.
