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
| GET | `/api/v1/platform/machinery?status=` | platform admin | the machinery page in one read: `health`, `capacity` and `jobs` (one status, newest 100) |
| GET | `/api/v1/platform/machinery/stream?status=` | platform admin (stream ticket) | SSE: health, voice capacity and one status of the queue as one `Machinery` snapshot; re-sent every 5s and at once when a voice seat frees |

## Jobs
- `reclaim_stalled_jobs` (queue `health`, every 5 min): a job left `doing` by a
  worker that died (its row pruned, so `worker_id` is null, or no heartbeat for
  `STALLED_AFTER_SECONDS`) is requeued once, then failed. procrastinate never
  does this itself: a pruned worker's jobs stay `doing` for ever.

`JobRead.events` is the job's procrastinate event log (type and time). A retry
logs `scheduled` before `deferred_for_retry`. procrastinate stores no exception
text, so the error itself is only in the worker log; keeping it needs a table
(and a migration) of its own.

## Cross-slice dependencies
None. Uses `core.db` and `core.redis` only. `service_jobs` is called from
above by `attempts` (the scoring job for an attempt) and by the platform
console's queue view.
