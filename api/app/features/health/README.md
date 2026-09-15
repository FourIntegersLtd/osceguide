# health

## Purpose
Liveness endpoint for Railway and for humans. Reports whether the database and Redis answer.

## Aggregates & invariants
None. This slice owns no tables.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | none | 200 `ok`/`degraded`, 503 `down` when the database fails |

## Jobs
None.

## Cross-slice dependencies
None. Uses `core.db` and `core.redis` only.
