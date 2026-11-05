# Support runbook

What a platform admin does about the tickets that actually arrive. Every read
and write below is a `/api/v1/platform/…` route behind `PlatformAdmin`, and
every write leaves an audit row readable at `GET /platform/audit`. The staff
console (`platform-web`, `/staff`) is the front of all of it: an account's
Attempts, Entitlements, Billing and History tabs, an attempt's inspector, the
Billing queue, the Audit log and Machinery.

| Ticket | See it | Fix it | Audit action |
|---|---|---|---|
| "No feedback" — transcript never arrived (attempt stuck `running`, turns exist) | `GET /platform/users/{id}/attempts?status=running`; detail shows `chunk_count > 0`, `transcript_complete: false` | `POST /platform/attempts/{id}/salvage` | `attempt.salvaged` |
| "No feedback" — transcript in, never marked (`interaction_complete`, no result; job missing or `failed`) | detail `scoring_job` / `jobs` | `POST /platform/attempts/{id}/rescore` (twice is once) | `attempt.rescore_requested` |
| "No feedback" — worker never fetched it (`has_definition: false`) or no turns | detail | `POST /platform/attempts/{id}/fail`, then a fresh attempt | `attempt.failed_by_admin` |
| "Paid, no access" — delivery refused (address had no account, plan missing) | `GET /platform/billing/events?failed_only=true`; `GET /platform/users/{id}/billing-events` | fix the cause, then `POST /platform/billing/events/{event_id}/replay` | `billing.event_replayed` |
| Paid outside Stripe (bank transfer, sponsor) | `GET /platform/users/{id}/payments` empty | `POST /platform/users/{id}/payments` | `billing.payment_recorded_manually` |
| Refund | payments list | refund in the Stripe dashboard, then `POST /platform/payments/{id}/refund` (record-only: revokes the grant, keeps the row) | `billing.refund_recorded`, `entitlement.revoked` |
| Goodwill / sponsored / extended access | `GET /platform/users/{id}/billing-access` (limit and why) | `POST /platform/users/{id}/payments` with a plan; omit `amount_total_pence` for free; `start` `now` or `after_current`; `send_receipt` only to email them. `…/revoke` withdraws | `billing.payment_recorded_manually` / `entitlement.revoked` |
| Organisation lapsed or suspended | `GET /platform/overview` → `at_risk` | `POST /platform/organizations/{slug}/contract` (dates + restore in one step) | `organization.contract_renewed` |
| Org admin locked out / wrong admin | `GET /platform/organizations/{slug}/memberships` | `…/memberships/{id}/restore`, `PATCH …/memberships/{id}` (role), `POST /platform/users/{id}/reset-password` | `membership.*`, `user.password_reset_sent` |
| Deactivate an account | `GET /platform/users/{id}` | `PATCH /platform/users/{id}` `{status: deactivated}` — sessions end now, token refused on next request | `user.deactivated` |
| Find an account, or everyone on an exam / paid / on trial / not started | `GET /platform/directory?q=&exam_code=&access=&status=&plan_code=`; `GET /platform/directory/summary` for the counts | — | — |
| "Let me sit this station again" (limit used up) | `GET /platform/users/{id}/stations` — `entry_attempts` is what the limit counts | `POST /platform/users/{id}/stations/{station_id}/reset-attempts` — counters to zero, attempts and marking kept | `user.station_attempts_reset` |
| "Wipe this station from my history" | same | `POST /platform/users/{id}/stations/{station_id}/delete-progress` `{reason}` — every attempt, transcript and marking gone, station removed from their sets; refused `attempt_in_progress` while one runs (fail it first) | `user.station_progress_deleted` |
| Exam date or extra reading time wrong | `GET /platform/users/{id}` | `PATCH /platform/users/{id}` `{exam_date, extra_reading_percent}` | `user.updated` |
| "Is the platform working?" | `GET /platform/health`, `GET /platform/jobs?status=failed`, `GET /platform/voice/capacity` | re-queue through the thing the job was about; no blind retry | — |

Decisions behind this (ADR 0020): platform admins read anything and act only
under `/platform/…`; they never inherit `OrgAdmin`. Refunds are record-only.
`failed` is terminal. No impersonation. No generic job retry.

## Database backups

Railway's Backups tab does not cover our custom Postgres image, so a nightly logical dump is the
only backup that survives losing the Railway project.

- **What runs.** The `db-backup` Railway service (source `api/infra/db-backup/`) exists in staging
  and production. It is a cron job (`0 2 * * *` UTC, restart policy never): `pg_dump -Fc
  --no-owner --no-privileges` over the private network, checked with `pg_restore -l`, uploaded with
  SSE-S3, size compared with the stored object, then dumps older than 30 days are deleted. Any failure
  fails the deploy run (red in Railway).
- **Where.** `s3://osceguide-platform/db-backups/nightly/<staging|production>/YYYY-MM-DD.dump`, one
  per night, about 30 days kept (about 130 MB each in production). `db-backups/manual/` holds hand-made dumps and
  is never pruned. The app signs only the folders `bucket_layout` lists, and `DB_BACKUPS` is reserved for this job.
- **Restore.** Download a dump and restore it into a fresh database, never over the live one:
  `aws s3 cp s3://osceguide-platform/db-backups/nightly/production/<date>.dump .`, then
  `createdb restored && pg_restore --no-owner --no-privileges -d restored <date>.dump`. The server
  needs pgvector (use `api/infra/postgres/Dockerfile`'s image, or `pgvector/pgvector:pg17` locally).
  `pg_restore -l` lists what the dump holds. Use pg_restore 17.x.
- **Run one by hand.** A deploy of a service that has a cron schedule does not run it; only the
  schedule does. To run now: in Railway, service `db-backup` → Settings → Cron Schedule, clear it,
  deploy (it runs once and stops), then put `0 2 * * *` back. Tested this way on 2026-11-04. Read the
  deployment log: it prints `uploaded key=… bytes=…`. Settings and variables:
  [ENVIRONMENT.md](ENVIRONMENT.md#database-backup-service).
- **Is it working?** The latest object under the prefix should be today's or yesterday's date. A
  failed night shows as a failed deployment of `db-backup`.

