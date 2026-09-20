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
