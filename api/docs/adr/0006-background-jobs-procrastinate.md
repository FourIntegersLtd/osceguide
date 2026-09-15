# 0006. Background jobs on procrastinate over Postgres

Date: 2026-09-15
Status: accepted

## Context
AI feedback takes minutes. b2c blocked a request for up to eight minutes and then spawned daemon threads; b2b spawned `threading.Thread`. Work was lost on every deploy and status lived in per-process dictionaries. Options: Celery or arq on Redis, or a Postgres-backed queue.

## Decision
procrastinate, with its job tables living in the application database (migration `0001`). Services enqueue inside the same transaction that changes the data the job acts on. One `worker` process type runs every task declared in `features/*/jobs.py`. Tasks are idempotent and keyed by the entity they process. Redis remains for ephemeral state only.

## Consequences
- No lost jobs across deploys or Redis restarts; the queue is inspectable with SQL.
- Job throughput is bounded by Postgres, which is ample at target scale.
- SQLAlchemy uses the psycopg 3 driver so the API and the queue share a connection dialect.
