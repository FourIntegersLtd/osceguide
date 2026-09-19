# 0020 — Platform support actions

**Status:** accepted, 2026-09-19.

## Context
The console could find an account and an organisation but fix nothing: no
view of a person's attempts, grants or payments; no way to re-queue a marking,
grant access, replay a refused payment, or read the platform's own audit rows.
The legacy systems did these by hand — a `has_paid` flag on the profile update,
scripts run with production credentials.

## Decisions
- **Read anything, act under `/platform/…`.** A platform admin may read any
  attempt, grant, payment or organisation. Every write is a `PlatformAdmin`
  route in the owning slice, idempotent or refused, and leaves an audit row
  with `org_id = NULL` via `tenancy.service_audit`. `OrgAdmin` keeps
  `allow_platform_admin=False`; the console's membership routes go through the
  same service and audit as the organisation's own.
- **Refunds are record-only.** Money moves in the Stripe dashboard; the API
  revokes the grant and keeps the payment (ADR 0012).
- **Manual payments are real payments.** `settle_payment` is one function for
  the webhook and the console, so a sponsor's seat takes no fewer steps.
- **`failed` is terminal.** Support fails a stuck attempt so a fresh one can
  start; nothing is resurrected. Salvage finishes a `running` attempt from its
  turns; rescore re-queues a marking and never overwrites a result.
- **Deactivation is immediate.** Refresh chains are revoked and `core.auth`
  checks the account's status per request through a seam `identity` binds.
- **No impersonation, no generic job retry.** Reads cover every case; a failed
  job is re-queued through the thing it was about.
