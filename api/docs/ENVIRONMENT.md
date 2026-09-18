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
| `MARKING_PRIMARY_MODEL` / `_EFFORT` | gpt-5-mini / low | Effort is set *explicitly* because unset means "medium" under any gpt-5 model — a cost decision nobody made. |
| `MARKING_FALLBACK_MODEL` / `ANTHROPIC_API_KEY` | claude-sonnet-4-5 | Fallback marking. |
| `WORKER_CONCURRENCY` | 4 | Background job parallelism. |
| `FRONTEND_URL` / `LOG_LEVEL` | localhost:3000 / INFO | Link building and logging. Logs become JSON automatically when deployed. |
| `SENTRY_DSN` | — | Error reporting, off unless set. Traces are sampled at 5% because an API the console polls would otherwise bill for its own heartbeat, and the request body is never sent — it holds passwords, legacy tokens and transcripts. |

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
read-only, scoped to `OSCEGuide-assessment-platform`, and give it an expiry:
a build argument is recorded in the image metadata and `docker history` will
show it. A builder that supports BuildKit secrets should use
`--mount=type=secret` instead, which records nothing.

The build ends with `python -c "import osce_assessment"`. That line is not
decoration. `poetry install` prints "Installing osce-assessment" and exits
zero even when the clone produced nothing, so without the check an image with
no marking engine builds green, starts, answers its health check, serves every
page and refuses the one thing it exists to do.
