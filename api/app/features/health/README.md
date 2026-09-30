# health

## Purpose
Liveness endpoint for Railway and for humans. Reports whether the database and Redis answer.

## Aggregates & invariants
None. This slice owns no tables. It is the one reader of procrastinate's own
tables (`procrastinate_jobs`, `procrastinate_workers`) — via `text()`, never a
mapping of ours, because their shape is the library's — so a slice above can
ask what the queue holds for the thing it is about without growing its own SQL.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | none | 200 `ok`/`degraded`, 503 `down` when the database fails |
| GET | `/api/v1/platform/health` | platform admin | the same report plus the queue by status and the worker's last heartbeat |
| GET | `/api/v1/platform/jobs` | platform admin | the queue, newest first; `?status=failed`, `?task=`, `?before_id=` to page. No retry route: re-queue through the thing the job was about |

## Jobs
None.

## Cross-slice dependencies
None. Uses `core.db` and `core.redis` only. `service_jobs` is called from
above by `attempts` (the scoring job for an attempt) and by the platform
console's queue view.
