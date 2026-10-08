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
- `inbox/` is in-app messages (site messages and announcements); staff compose them from
  `domains/platform` (Announcements, MessagesInbox). Learner and org screens read via
  `capabilities/inbox`.
- `public_site/` is the marketing site's backend: unauthenticated. The public pages (`app/(public)`) compose `domains/marketing`.
- Sitting emails (cancel, edit, reminder) are owned by the sitting's owner, `institution-owner`.
