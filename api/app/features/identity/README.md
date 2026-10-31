# identity

## Purpose
Who someone is, and proving it. Owns `users`, their credentials, their external
identities and their refresh tokens. Issues the platform access token every other
slice reads.

This replaces three separate answers: b2c's Firestore user documents with a bcrypt
hash and a 30-day cookie JWT, b2c's Clerk SSO path for white-label tenants, and
b2b's `b2b_users` row with an **unsalted SHA-256** hash and its own 30-day JWT.
One person with one email is one row here, whatever they bought or were invited to.

## Use cases
- As a **consumer**, I register with an email and password so that I can practise.
- As **anyone**, I sign in and receive an access token and a refresh token.
- As **anyone**, I exchange a refresh token for a new access token without signing in again.
- As a **user of a retiring backend**, I trade the session I already have
  for a platform one, without setting a new password.
- As **anyone**, I sign out so that my refresh token stops working.
- As **anyone**, I request a password reset and set a new password with the emailed token.
- As a **user invited by my institution**, I receive a link, choose a password, and sign
  in. Until then the account has no password and cannot sign in at all.
- As an **SSO user**, I sign in through my institution's provider and get the same
  platform token as everyone else.
- As **anyone**, I read my own profile and memberships.

## Aggregates & invariants
**User** is the aggregate root; credentials, external identities and refresh tokens
live inside it and are never addressed independently.

- `email` is unique, case-insensitive. The migration merges b2c's four `*_users`
  collections and `b2b_users` on the lowercased address.
- A current password is stored only as an argon2id hash in `password_hash`. No SHA-256, salted or
  otherwise. The one exception is `legacy_password_hash`, a b2c bcrypt hash carried by the import: sign-in
  accepts it once, after `password_login_disabled` and only when `verify_password` fails, and replaces it
  with argon2id in one UPDATE (`set_password_hash`, no forced change). Any password set or reset
  nulls it. A legacy hash buys no exemption from suspension, the second factor, reopening or the trial
  clock. Dropped at decommission (`migration/README.md`).
- The three routes an attacker gains something by repeating — sign-in, password
  reset and the legacy exchange — are rate limited per caller address
  (`core.rate_limit`). It **fails open**: an unreachable Redis allows the call,
  because a cache outage must not become an outage of signing in. It raises the
  cost of password spraying; it was never the only thing in the way.
- The legacy bridge verifies, never mints: the retiring backends' signing secrets are read
  only to check a signature, an arm with no secret configured refuses every
  exchange, and an address with no row here is refused rather than created. What
  the legacy token claims about roles, payment or org membership is ignored —
  memberships come from this database, so a thirty-day-old claim cannot widen
  anyone's access.
- An access token lives 15 minutes; a refresh token is single-use and rotates —
  presenting a rotated token revokes the whole chain (reuse detection).
- `must_change_password` gates every route except reading yourself and changing it.
- Changing the password revokes every refresh chain and answers a fresh
  `TokenPair`, so the device that changed it stays signed in. Other devices
  keep their access token until it expires, so they are signed out within 15
  minutes, not at once. An SSO-only account is refused
  `password_login_disabled`, one with no hash yet `password_not_set` (never an
  `invalid_credentials` no guess could pass), and a suspended one
  `account_suspended`, as sign-in refuses it.
- Platform admin is a column on `users`, not an email list and not a membership in
  a reserved org.
- Registering never grants an org membership. Access comes from `entitlements`.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/auth/register` | none | 201; `email_taken` (409), `weak_password` (422) |
| POST | `/api/v1/auth/login` | none | `invalid_credentials` (401), `account_suspended` (403), `too_many_requests` (429). A second factor answers `200` with `status` `mfa_required` or `mfa_enrolment_required` instead of tokens |
| POST | `/api/v1/auth/mfa/verify` | challenge | `invalid_mfa_code` (401), `mfa_challenge_expired` (401), `mfa_not_enrolled` (409), `too_many_requests` (429) |
| POST | `/api/v1/auth/mfa/enrol/start` | enrolment challenge | returns the secret once |
| POST | `/api/v1/auth/mfa/enrol/confirm` | enrolment challenge | tokens plus ten recovery codes, shown once |
| GET | `/api/v1/me/mfa` | bearer | enrolled or not, and why it is required |
| POST | `/api/v1/me/mfa/enrol` | bearer | voluntary enrolment |
| POST | `/api/v1/me/mfa/confirm` | bearer | |
| POST | `/api/v1/me/mfa/recovery-codes` | bearer | needs a current code |
| DELETE | `/api/v1/me/mfa` | bearer | `mfa_required_by_policy` (409) when policy still requires it |
| POST | `/api/v1/auth/refresh` | refresh token | `invalid_refresh_token` (401) on reuse or expiry |
| POST | `/api/v1/auth/exchange-legacy` | a token from the retiring backend | `invalid_legacy_token` (401), `legacy_account_not_imported` (401), `legacy_exchange_unavailable` (503). Deleted at decommission |
| POST | `/api/v1/auth/logout` | bearer | revokes the presented chain |
| POST | `/api/v1/auth/password-reset` | none | always 202; never reveals whether the email exists; `too_many_requests` (429) |
| POST | `/api/v1/auth/password-reset/confirm` | reset token | `invalid_reset_token` (422) for unknown, spent or expired; `weak_password` (422); `too_many_requests` (429). Only the first is about the link: the form says the others as themselves |
| POST | `/api/v1/me/email-change` | user | password-proved; mails a one-hour signed link to the new address; always 202 whether or not the address is held; nothing is stored (no migration) |
| POST | `/api/v1/auth/email-change/confirm` | change token | moves the account email, ends every session, roster entries follow, old address is told; `invalid_email_change_token` (422) for forged, spent, expired or since-taken |
| POST | `/api/v1/auth/change-password` | bearer | the only route allowed while `must_change_password` |
| POST | `/api/v1/auth/stream-ticket` | bearer | a 60-second credential for one `EventSource` (ADR 0015) |
| GET | `/api/v1/me` | bearer | profile, memberships, active workspace |

## Jobs
`send_password_reset_email`, `send_welcome_email` and the invitation — enqueued in
the same transaction as the row they concern. `service_invitations.invite_user`
is what `tenancy` and `roster` call for an address with no account: the token it
mails is an ordinary reset token, so `password-reset/confirm` finishes the job.
`service_invitations.reissue_invitation` is the same email for an account that
has one and has not used it — it mints a fresh token, because only the hash of
the first was ever stored, and refuses an account that already has a password.
`service_invitations.send_due_invitation_reminders` (daily job `send_invitation_reminders`)
sends the reminder once, five days in: an invitation whose link has under two days left, with
no password set. It reissues through the same path with `reminder=True`; the reminder's own
message is `invitation_reminder`, which is not remindable, so nobody is nudged twice. The
original wording (`invited_to`, `exam_title`) is read back from the outbox
(`notifications.queued_under`), since only the token hash is stored here.

## The exam an account is for
`users.exam_code` is set at sign-up and changed on `PATCH /me`. The retiring
client took it from the hostname — `sca.osceguide.com` — so a person only ever
saw one exam and the product had no switcher at all; on one domain it has to be
recorded.

A code rather than a foreign key, and unvalidated here, because this slice sits
below `catalog` and may not resolve one. It grants nothing: what somebody may
open is `entitlements`' answer, and `entitlements.service_access` filters this
through the published catalogue, so a code naming no exam yields nothing.

## Cross-slice dependencies
None. `tenancy` reads users through this slice's service; this slice never reads
`tenancy`. Memberships reach the token because the login service asks `tenancy` for
them — the call goes downward, from `tenancy` into `identity`, never back.

## Closing, reopening and erasing an account

Closing keeps the password hash for 30 days and audits `account.closed`. Signing in with the password inside
that month reopens the account (SSO sign-in does not yet), but only once sign-in is complete: the password
path reopens in `service_mfa._issue_session`, so a second-factor challenge leaves it closed; the password
check uses `can_reopen`, which changes nothing. After 30 days `erase_due_accounts` erases each
account in its own session, so one failure is logged and the rest still run; it also blanks the account's
roster entries and queued release emails. Decision rationale stays in the append-only table (needs a migration).
