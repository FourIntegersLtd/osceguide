# OSCE Guide Platform API

The single backend for every OSCE Guide product: consumer exam practice, institutional exam programmes, partner reporting, and the routes the LiveKit workers call. It replaces `b2b-api` (FastAPI + Supabase client) and `b2c-api` (Flask + Firestore).

## Stack

| Concern | Choice | Why (see `docs/adr/`) |
|---|---|---|
| Web | FastAPI, Pydantic v2 | Typed request/response models produce the OpenAPI contract the frontend consumes |
| Database | Postgres (Supabase-hosted) via SQLAlchemy 2.0 async + psycopg 3 | Transactions, foreign keys, one query language |
| Migrations | Alembic | Tracked, repeatable, run in CI and on deploy |
| Jobs | procrastinate (Postgres-backed) | Enqueue in the same transaction as the data it acts on |
| Ephemeral state | Redis | Cache, rate limits, SSE fan-out, LiveKit cloud-slot counters |
| Identity | Own `users` table, platform JWT, pluggable IdPs | One login for every product; Clerk SSO is a provider, not the owner |
| Logging | structlog | JSON in deployed environments, request id on every line |

## Run it

```bash
cp .env.example .env
make install
make db-up        # Postgres on :5433, Redis on :6380
make migrate
make start        # http://localhost:8002/docs
make worker       # in a second terminal
```

## Test it

```bash
make test-unit    # no database needed
make test         # needs Docker running (testcontainers) or TEST_DATABASE_URL
make ci           # lint, types, architecture rules, tests
```

## Layout

```
app/
  main.py            composition root: the only place routers are mounted
  core/              shared kernel; never imports app.features
  features/<slice>/  one bounded context per package
    README.md        purpose, aggregates, routes, jobs, dependencies (CI enforced)
    router.py        HTTP only: parse, call service, return schema
    schemas.py       request/response models (the API contract)
    service.py       use cases; raises AppError subclasses
    repository.py    SQLAlchemy queries; org-scoped methods take org_id first
    models.py        ORM tables
    domain.py        pure rules and state machines; no IO
    errors.py        slice error types
    jobs.py          procrastinate tasks (optional)
  worker/main.py     background worker entrypoint
alembic/             migrations
tests/               unit/ repository/ http/ contract/ against real Postgres
docs/adr/            architecture decision records
```

Read `CONTRIBUTING.md` before adding a slice.

## Environments

`APP_ENV` is one of `local`, `test`, `staging`, `production`. Staging and production refuse to start without `JWT_SECRET`, `WORKER_SECRET` and `DATABASE_URL`.

## Ports and URLs

| Service | Local |
|---|---|
| API | http://localhost:8002 |
| OpenAPI | http://localhost:8002/docs |
| Health | http://localhost:8002/health |
| Public API prefix | `/api/v1` |
| Worker routes prefix | `/api/worker` (guarded by `X-Worker-Secret`) |
