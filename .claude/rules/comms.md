---
paths:
  - "api/app/features/{notifications,inbox,public_site}/**"
  - "web/src/capabilities/inbox/**"
  - "web/src/app/(public)/**"
  - "web/src/app/**/{inbox,messages}/**"
---
# Comms: what to know

Owners: `access-owner` (outbox, notifications), `web-foundation-owner` (inbox web),
`content-owner` (public site backend). Proof: `verify-access` for anything that sends email.

- Email goes through the outbox (`notifications/`): a row is written in the same transaction as the
  event, then a job claims and sends it (`claimed_at`), with idempotency columns on scheduled emails.
  Prove an email change by reading the outbox row; an invitation or reset that "does not arrive" is
  an outbox or job problem first.
- `deliver_due` takes a session opener, not a session, and holds no transaction across a send: one
  session reclaims stale rows and claims a batch (`processing`) and commits, the sends run
  `outbox_send_concurrency` at a time, a second session records sent/retry/failed. A worker that dies
  between the steps leaves `processing` rows that `reclaim_stale` returns, so a send can repeat once.
  Set `OUTBOX_DELIVERY_BATCH` and `OUTBOX_SEND_CONCURRENCY` to the Resend rate. `ResendSender` sets its
  key at construction and sends in a thread under a 20 s timeout; a new sender must not block the loop.
- `inbox/` is in-app messages (site messages and announcements); staff compose them from
  `domains/platform` (Announcements, MessagesInbox). Learner and org screens read via
  `capabilities/inbox`.
- `public_site/` is the marketing site's backend: unauthenticated. The public pages (`app/(public)`) compose `domains/marketing`.
- Sitting emails (cancel, edit, reminder) are owned by the sitting's owner, `institution-owner`.

## What a failure looks like here
- An email is sent outside the outbox, or the outbox row is written outside the event's transaction.
- A job sends the same email twice (no claim or idempotency), or never sends it.
- An email names someone who was erased, or goes to the wrong person.
