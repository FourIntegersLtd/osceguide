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
  A **timed-out** Resend call is abandoned (`failed`), not retried: the thread may still complete and
  auto-retry would risk a duplicate. Set `OUTBOX_DELIVERY_BATCH` and `OUTBOX_SEND_CONCURRENCY` to the
  Resend rate. `ResendSender` sets its key at construction and sends in a thread under a 20 s timeout;
  a new sender must not block the loop.
- `inbox/` is in-app messages (site messages and announcements); staff compose them from
  `domains/platform` (Announcements, MessagesInbox). Learner and org screens read via
  `capabilities/inbox`.
- `public_site/` is the marketing site's backend: unauthenticated. The public pages (`app/(public)`) compose `domains/marketing`.
- Sitting emails (cancel, edit, reminder) are owned by the sitting's owner, `institution-owner`.
- **Candidate reminders** (`sittings/service_notify.send_candidate_reminders`, run by the `send_exam_day_reminders` job, now every
  5 min, not a task of its own: a new task raises the `NO_OWN_STATE_CEILING` guard): template `sitting_reminder`, kinds `day_before` (starts in 1-24 h) and `hour_before` (last hour), key
  `candidate-reminder:{kind}:{sitting}:{user}:{start minute}` so a moved sitting reminds again and nothing else repeats.
  Skips cancelled/completed sittings, suspended orgs, finished circuits, and roster rows with `access_revoked` (the
  roster, not `memberships`, is the truth: test helpers roster people without a membership). Supervisors are not
  candidates. A sitting booked under 24 h out gets its `day_before` on the next run. There are no per-org comms
  settings, so none are consulted; add one before adding a second reminder kind.
- Candidate email wording: the payload carries `hire: "1"` for an `employer` org and `_sitting_word` turns "sitting"
  into "assessment" (visible text only; routes still say `/sittings`). `sitting_scheduled` and `sitting_reminder` end
  with "Test your setup", `/app/{org}/trainee/tech-check`: the candidate's own signed-in page, so the link carries no
  token, address or id. Do not put a signed token in it; sign-in is the identity.

## What a failure looks like here
- An email is sent outside the outbox, or the outbox row is written outside the event's transaction.
- A job sends the same email twice (no claim or idempotency), or never sends it.
- An email names someone who was erased, or goes to the wrong person.
