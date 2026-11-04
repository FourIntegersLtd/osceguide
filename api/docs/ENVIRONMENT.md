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

Staging and production refuse to boot without every name in
`REQUIRED_WHEN_DEPLOYED` (`app/core/settings.py`). `JWT_SECRET` must also be at
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
| `OPENAI_API_KEY` | — | Primary marking model. Jobs fail and retry without it; transcripts are kept. Also embeds Athena's material index (reading and help); without it the tutor says it cannot look things up. |
| `PAYOUT_DETAILS_KEY` | local Fernet key | Encrypts a referrer's bank details. A missing key refuses to encrypt rather than storing plaintext. |
| `MFA_SECRET_KEY` | local Fernet key | Encrypts a TOTP shared secret at rest, the same way `PAYOUT_DETAILS_KEY` encrypts bank details. Recovery codes are hashed, not encrypted. A missing key refuses to enrol rather than storing the secret in plaintext. |

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
| `LIVEKIT_SELF_HOSTED_SEATS` | 18 | Assessment sessions our own workers take at once: replicas x `LIVEKIT_ASSESSMENT_MAX_CONCURRENT_JOBS` (production: one replica per worker node, 6 each; staging 1 x 2). Past these and Cloud's, candidates wait in line. In production `infra/ansible/add-worker.sh` / `remove-worker.sh` set it when they change the nodes. `GET /platform/voice/capacity` reports it as `self_hosted_seats_total` beside the seats taken. |
| `LIVEKIT_QUEUE_WAITER_TTL_SECONDS` | 90 | How long a waiter keeps their place with nobody watching it. Must exceed the stream heartbeat (25s). |
| `SUPPORT_EMAIL` | hello@osceguide.com | The mailbox people are told to write to, and what safety reports and spend alerts are sent to. The envelope sender derives from it, so blank refuses to boot. |
| `EMAIL_FROM` | `OSCE Guide <SUPPORT_EMAIL>` (derived) | Envelope sender. Set it only where the sender and the reply-to inbox differ; Resend refuses a sender off its verified domain. |
| `STRIPE_SECRET_KEY` | — | Checkout. **Not** in the required ten, so a deploy can boot without being able to sell. |
| `CLERK_SECRET_KEY` / `CLERK_PUBLISHABLE_KEY` | — | Partner SSO, brokered through Clerk. **Not** in the required ten: a deploy without them simply cannot offer SSO, and `POST /auth/sso/login` and `/callback` refuse with `sso_login_unavailable` rather than trusting an unverified token. The organisation's `issuer` carries its Clerk frontend domain. |
| `MARKING_PRIMARY_PROVIDER` | openai | `openai` or `anthropic` (anything else refuses to boot): which provider marks first, for scoring and live coverage. The other answers if it fails or its key is missing. Unset keeps OpenAI first; Railway needs it only to switch. The model vars below keep their slot: `MARKING_PRIMARY_MODEL` is always the OpenAI model, `MARKING_FALLBACK_MODEL` the Anthropic one. |
| `MARKING_PRIMARY_MODEL` / `_EFFORT` | gpt-6-luna / low | Effort is set *explicitly* because unset means "medium" under any gpt-5 model — a cost decision nobody made. |
| `MARKING_FALLBACK_MODEL` / `ANTHROPIC_API_KEY` | claude-sonnet-5-5 | Fallback marking. Sends no temperature and no forced tool_choice (both 400 on Claude 5.5); when its reply misses the schema it is sent the exact errors in the same conversation (`tool_result` with `is_error`), twice, before the mark is refused. |
| `WORKER_CONCURRENCY` | 4 | Background job parallelism. |
| `DATABASE_SIZE_BUDGET_MB` | 500 | The host's database quota in MiB (the free plan flips the database read-only at 500 MB). `GET /platform/health` measures live against it and the Ops screen shows the biggest tables and a forecast. The daily `record_database_size` task stores a reading; crossing 60% writes one `database.size_warning` audit row, crossing 80% one `database.size_critical` row and a Sentry message. Both fire once per crossing, and only while the worker runs. |
| `JOB_HISTORY_RETENTION_DAYS` | 14 | The daily `prune_job_history` task deletes succeeded jobs this many days after they finish (procrastinate's `delete_old_jobs`; their events go with them). Failed jobs stay for staff to retry. |
| `FRONTEND_URL` / `LOG_LEVEL` | localhost:3000 / INFO | Link building and logging. Logs become JSON automatically when deployed. |
| `RAILWAY_GIT_COMMIT_SHA` | — | Set by Railway on every deploy, never by hand. `/health` reports it as `commit`, so anyone can see what staging or production runs; the promote workflow refuses a commit staging is not running. |
| `SENTRY_DSN` | — | Error reporting, off unless set. Traces are sampled at 5% because an API the console polls would otherwise bill for its own heartbeat, and the request body is never sent — it holds passwords, legacy tokens and transcripts. |
| `CARTESIA_API_KEY` | — | TTS for slide and podcast production. Jobs raise `av_unavailable` without it. |
| `AWS_REGION` / `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | — | Access to the file bucket. The bucket itself is fixed in code (`core.bucket_layout.BUCKET`), not a setting. Jobs raise `av_unavailable` without credentials. |
| `MEDIA_AV_FONT_DIR` | — | Optional extra font directory for slide video. Empty uses the bundled fonts. |
| `ENGAGEMENT_EMAIL_ENABLED` | false | Gates `identity.jobs.send_engagement_emails`, the daily "come try a station" nudge to a signed-up person who never ran a practice station (ported from legacy `b2c-api`'s `InactiveUserEngagementService`). Off by default so a freshly migrated environment cannot fire it on real inboxes until the owner switches it on deliberately. |

## Local gotcha

A populated local `.env` has been observed breaking tests in the legacy `b2b-api` —
worker-secret and LiveKit values leak into the test run and five tests fail. Those
failures are environmental, not regressions. Check what your `.env` is injecting before
chasing a red suite.

## Building the image

The image builds from the **repository root**, because the marking engine it
installs lives beside the api in `assessment/packages/osce_assessment`:

```bash
docker build -f api/Dockerfile .
```

The root `.dockerignore` sends only `api/` and the engine package to the
builder. No token or build argument is needed; the engine is a path
dependency in `pyproject.toml`, copied in before `poetry install`.

The build ends with `python -c "import osce_assessment"`. That line is not
decoration. `poetry install` prints "Installing osce-assessment" and exits
zero even when the package produced nothing, so without the check an image with
no marking engine builds green, starts, answers its health check, serves every
page and refuses the one thing it exists to do.

## Staging and production

Two Railway environments in the "OSCE Guide server backend" project, each with
its own platform-api, platform-worker, Postgres (`platform-postgres`, our
pgvector image in `infra/postgres/`) and Redis. Nothing is shared between them.

| | Staging | Production |
|---|---|---|
| Deploys from | `main`, by itself after every push | `production-api`, moved only by the promote workflow |
| `APP_ENV` | `staging` | `production` |
| Data | Seeded test data only (`scripts/seed_platform.py`) | Real people |
| LiveKit project | `new-test-agent` | the production project |
| Stripe | test-mode keys and webhook | live keys and webhook |
| `JWT_SECRET`, `WORKER_SECRET` | its own | its own, never copied to staging |

**Getting a change to production.** Merge to `main`; CI runs and Railway deploys
staging. Test it there. Then GitHub → Actions → "Promote api to
production" → Run workflow. It checks the commit is on `main`, CI passed, staging
runs it and is healthy, and a test account can sign in on staging and read its
dashboard; then it fast-forwards `production-api`, and Railway deploys it. `/health`
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
| Source → Branch | `main` on staging, `production-api` on production | same |
| Source → Root directory | `/` (the engine sits outside `api/`) | `/` |
| Build → Builder / Dockerfile path | Dockerfile, `/api/Dockerfile` | same |
| Build → Watch paths | `/api/**`, `/assessment/packages/osce_assessment/**` | same |
| Deploy → Custom start command | empty (the Dockerfile's `uvicorn`) | `python -m app.worker.main` |
| Deploy → Pre-deploy command | `alembic upgrade head` | empty, so two migrators never race |
| Deploy → Healthcheck path | `/health` | empty (the worker serves no HTTP) |
| Deploy → Teardown → Overlap seconds | `20`, so the old copy answers until the new one is serving | default |
| Deploy → Teardown → Draining seconds | `30`, so requests in flight finish before the old copy is killed | default |

Railway runs the pre-deploy command in its own step, and its output is not in the
deploy log. After a deploy with a migration, check that the worker's jobs succeed
and `/health` reports the new commit.

### Database backup service

`db-backup` (staging and production) is a cron service built from `api/infra/db-backup/`. Its settings
live in Railway, not in a `railway.json`: the file was not read for this service (checked
2026-11-04; Config as Code ends 2026-12-01), so the cron schedule is set on the service.

| Setting | Value |
|---|---|
| Source | none yet: deployed with `railway up` from `api/infra/db-backup/` (`--service db-backup --environment <env>`). Connect the repo, root `/api/infra/db-backup`, when you want a push to redeploy it |
| Build → Dockerfile path | `Dockerfile` |
| Deploy → Cron Schedule | `0 2 * * *` (UTC) |
| Deploy → Restart policy | Never |
| Variables | `DATABASE_URL=${{<postgres service>.DATABASE_URL}}` (`platform-postgres` / `platform-postgres-production`), `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` referenced from the api service (`platform-api-staging` / `platform-api`), `BACKUP_ENV=staging` or `production` |

The bucket is versioned: a pruned nightly dump gets a delete marker and its bytes stay until a lifecycle
rule expires old versions (the app's key cannot set one).

