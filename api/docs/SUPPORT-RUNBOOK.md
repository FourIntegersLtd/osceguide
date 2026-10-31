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
| Renewal / extension / goodwill access | `GET /platform/users/{id}/entitlements` | `PATCH /platform/entitlements/{id}` to move the end; `POST /platform/users/{id}/entitlements` to grant (`source: admin`); `…/revoke` | `entitlement.extended` / `.granted` / `.revoked` |
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

## Reclaiming transcript disk (one-off, delete after the run)

`transcript_messages` held one row per spoken turn (744k rows, ~260 MB with indexes). Finished attempts
now fold into `transcripts.messages`; the worker has never run the periodic task on production, so
`scripts/compact_transcripts.py` folds the existing ones by hand. Usage, flags, exit codes and the
connection rules (session pooler port 5432, never 6543; no `.env` read) are in the script's docstring.
When the periodic `compact_transcripts` task runs on production, delete the script, its test, this
section and the matching lines in `.claude/rules/staff-console.md` in one commit.

Run in this order from `api`, with `DATABASE_URL` exported: plain (report only), `--yes` (backfill),
`--yes --vacuum`, then `--yes --vacuum --full` last.

`SUPABASE_PROD_DB_URL` lives in `api/.env` and is not exported by a shell, so naming it alone leaves
`DATABASE_URL` empty and alembic migrates **localhost** instead. Export it first, swapping the
transaction pooler for the session one, and never echo it:

```bash
export DATABASE_URL=$(grep -E '^SUPABASE_PROD_DB_URL=' .env | head -1 | cut -d= -f2- | tr -d '"'"'" )
export DATABASE_URL=${DATABASE_URL/:6543/:5432}
[ -n "$DATABASE_URL" ] && echo "target: ${DATABASE_URL##*@}"
```

**Expected sizes** (`pg_database_size`, which is what the quota counts; the Supabase dashboard lags).
Assumption: about 10 MB of `transcript_messages` is still rows after the backfill (attempts not yet
finished, or inside the one-hour grace). The script prints the real figure at every step.

| Stage | Database | `transcript_messages` |
|---|---|---|
| Now | ~387 MB | ~260 MB, 744k rows |
| After step 2 (backfill) | **higher**, ~437 MB (+~50 MB of documents, which stay) | unchanged: dead rows are not returned |
| After step 3 (plain `VACUUM`) | between ~437 MB (an unfinished attempt's rows sit at the table's end, so nothing truncates) and ~285 MB (nothing does); indexes keep their size | same |
| After step 4 (`VACUUM FULL`) | **~190 MB**: 387 + 50 - 260 + the remaining ~10 MB | ~10 MB. If it is more, the database is ~177 MB plus that |

Locally (900 attempts, 72k rows, 10 unfinished at the tail): 40.3 MB, backfill 41.5 MB, `VACUUM` 41.5 MB
(no change), `VACUUM FULL` 14.8 MB, table 27.1 to 0.3 MB. With no unfinished attempt, plain `VACUUM` took
46.3 to 30.3 MB.

**Traps.**
- **Step 2 grows the database before it shrinks it.** If headroom to the quota is under ~60 MB, Ctrl-C part
  way, run step 3, and continue; newest-first means each step 3 hands back the part just emptied.
- **`VACUUM FULL` takes an exclusive lock** on `transcript_messages` (seconds when small). Run it when nobody
  is mid-attempt. A long-open transaction elsewhere (`pg_stat_activity`) holds back what `VACUUM` may remove.
- **Read-only host.** Over quota, the host may refuse writes. The script stops and prints how to retry; it does
  not change the setting.
- **Stopped part way** (Ctrl-C, dropped connection, exit 1 naming attempt ids): nothing to undo; each attempt is
  its own transaction. Fix the cause for those ids and re-run. The script does not vacuum after a failure.
