# Exam-burst load test (k6)

Every VU is one candidate at the same buzzer: login, dashboard, station library, start an attempt,
(optionally) take a voice token, wait for the buzzer, post the worker transcript, then wait on
`/me/events` (SSE, no polling) for the mark. It records `marking_latency` (transcript accepted to
`evaluated`/`failed`).

## LiveKit cap

LiveKit allows only **50 concurrent voice sessions** today. `VOICE_VUS` (default 50, never more than
`VUS`) is how many VUs call `POST /attempts/{id}/voice-token`. The others skip voice and drive the
worker routes directly, so the api, DB and marking are still loaded at `VUS` (default 50). Raise
`VUS` above 50 only for HTTP-only runs, and keep `VOICE_VUS` at or under the LiveKit grant.

## Build k6 with SSE

Stock k6 has no SSE client. Build one (needs Go and `xk6`):

```bash
xk6 build --with github.com/phymbert/xk6-sse -o ./k6sse
```

## Seed (staging or local only)

`scripts/seed_loadtest.py` refuses unless the database host is local or contains `staging`.

```bash
cd api
DATABASE_URL=<staging or local url> PYTHONPATH=. poetry run python scripts/seed_loadtest.py --count 50
```

Creates `trainee1..N@load-test.example.com` (one shared password, `LOAD_PASSWORD`, default
`Load-test-password-1!`), each with a live grant on `sca`, and one published library station if the
exam has none. Safe to re-run. (`.test` addresses are rejected by the email validator.)
The seed needs a migrated database with `scripts/seed_platform.py` already run.

## Run

```bash
./k6sse run \
  -e BASE_URL=https://<staging-api> \
  -e WORKER_SECRET=<staging WORKER_SECRET> \
  -e VUS=50 -e VOICE_VUS=50 \
  api/loadtest/exam_burst.js
```

| Env | Default | Meaning |
|---|---|---|
| `BASE_URL` | `http://localhost:8002` | api origin |
| `WORKER_SECRET` | empty | the api's `WORKER_SECRET`; header name `WORKER_SECRET_HEADER` (default `X-Worker-Secret`) |
| `VUS` | 50 | candidates; VU n signs in as `trainee{n}`, so seed at least `VUS` |
| `VOICE_VUS` | 50 | VUs that request a voice room (capped at `VUS`) |
| `BUZZER_DELAY_S` | 30 | seconds from start until all VUs submit together |
| `WAIT_MARKING` | true | false: skip the SSE wait (no marking worker, e.g. a local run); the SSE module is still imported, so use the xk6 build or a stub |
| `MARKING_TIMEOUT_S` | 600 | per VU, then counted in `marking_missed` |
| `EXAM_CODE`, `LOAD_PASSWORD`, `MAX_DURATION` | `sca`, see above, `25m` | |

## Staging settings for the run

Sign-in is limited per address (300 a minute, `core/rate_limit.py` `SIGN_IN_ADDRESS`) because every
VU comes from one IP. With `VUS` up to 300 that holds; above that raise the allowance on staging for
the run (the plan names `SIGN_IN_PER_ADDRESS_PER_MINUTE=100000`; that setting does not exist yet, so
until it does the limit is the constant). Put the staging `WORKER_SECRET` in your shell, never in the repo.

## Thresholds (the run fails if any is crossed)

- `http_req_duration{phase:start}` p95 under 500 ms (`POST /attempts`)
- `http_req_duration{phase:submit}` p95 under 500 ms (worker transcript)
- `http_req_failed` under 0.1%
- `checks{kind:no429}` 100% (no request was rate limited)
- `checks{kind:flow}` 100% (every step returned its expected status, every mark arrived `evaluated`)
- `marking_latency` p95 under 300 s

## What to watch while it runs

- `pg_stat_activity` count under 80% of `max_connections`.
- Procrastinate `todo` jobs (queue depth, and how fast it drains at the marking concurrency).
- Sentry (platform-api and platform-worker): expect no new errors.
- Railway CPU and memory for platform-api and the workers.

Run at least 48 h before a big exam, at the booked cohort size, on staging sized like production.
