# health

## Purpose
Liveness endpoint for Railway and for humans. Reports whether the database and Redis answer, and whether every published platform station is bound to a template (`checks.content`, `degraded` when not).

## Aggregates & invariants
One table, `database_size_readings`: one row per day of how big the database is and which tables are the weight (the history the forecast is fitted to). It is also the one reader of procrastinate's own
tables (`procrastinate_jobs`, `procrastinate_workers`) — via `text()`, never a
mapping of ours, because their shape is the library's — so a slice above can
ask what the queue holds for the thing it is about without growing its own SQL.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | none | 200 `ok`/`degraded`, 503 `down` when the database fails |
| GET | `/api/v1/platform/health` | platform admin | the same report plus the queue by status, the worker's last heartbeat and `database_size` (measured live, not from the worker: total, percent of `DATABASE_SIZE_BUDGET_MB`, level, top ten relations with bytes per row, and a forecast that says so when there is too little history; null when the read fails) |
| GET | `/api/v1/platform/jobs` | platform admin | the queue, newest first; `?status=failed`, `?task=`, `?before_id=` to page. No retry route: re-queue through the thing the job was about |
| GET | `/api/v1/platform/outbox/undelivered` | platform admin | email the outbox abandoned after its last attempt, newest first: the newest 100 (`UNDELIVERED_PAGE`) and `has_more` |
| POST | `/api/v1/platform/outbox/{message_id}/retry` | platform admin | queue an abandoned email again with fresh attempts; audited; `message_not_retryable` once it is not abandoned |
| GET | `/api/v1/platform/machinery?status=` | platform admin | the machinery page in one read: `health`, `capacity` and `jobs` (one status, newest 100) |
| GET | `/api/v1/platform/machinery/stream?status=` | platform admin (stream ticket) | SSE: health, voice capacity and one status of the queue as one `Machinery` snapshot; re-sent every 5s and at once when a voice seat frees |

## Jobs
- `reclaim_stalled_jobs` (queue `health`, every 5 min): a job left `doing` by a
  worker that died (its row pruned, so `worker_id` is null, or no heartbeat for
  `STALLED_AFTER_SECONDS`) is requeued up to three times (procrastinate's own
  `attempts` is the persisted count), then failed with a `job.stalled_failed`
  row in the platform audit log. procrastinate never does this itself: a pruned
  worker's jobs stay `doing` for ever.
  The same sweep (`run_sweep`) fails consumer attempts left created or running
  over three hours with `failed_reason` `abandoned`, and each step runs in its
  own transaction: a step that raises writes `sweep.failed` to the platform
  audit log (`GET /platform/audit?action=sweep.`) and the next step still runs.
- `record_database_size` (queue `health`, daily 04:30): stores today's reading
  (idempotent on the day) and, when the level rose, writes `database.size_warning`
  (60% of budget) or `database.size_critical` (80%, also a Sentry message) to the
  platform audit log, once per crossing. Readings older than 400 days are trimmed.
- `prune_job_history` (queue `health`, daily 04:45): procrastinate's
  `delete_old_jobs` for succeeded jobs older than `JOB_HISTORY_RETENTION_DAYS`
  (events go with them by cascade), with a `jobs.pruned` audit row. Failed jobs
  stay: staff retry them.
  Both write `sweep.failed` to the audit log when they raise.

`JobRead.events` is the job's procrastinate event log (type and time). A retry
logs `scheduled` before `deferred_for_retry`. procrastinate stores no exception
text, so the error itself is only in the worker log; keeping it needs a table
(and a migration) of its own.

## Cross-slice dependencies
None. Uses `core.db` and `core.redis` only. `service_jobs` is called from
above by `attempts` (the scoring job for an attempt) and by the platform
console's queue view.
