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
- A password is stored only as an argon2id hash. No SHA-256, salted or otherwise.
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
- Platform admin is a column on `users`, not an email list and not a membership in
  a reserved org.
- Registering never grants an org membership. Access comes from `entitlements`.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/auth/register` | none | 201; `email_taken` (409), `weak_password` (422) |
| POST | `/api/v1/auth/login` | none | `invalid_credentials` (401), `account_suspended` (403), `too_many_requests` (429) |
| POST | `/api/v1/auth/refresh` | refresh token | `invalid_refresh_token` (401) on reuse or expiry |
| POST | `/api/v1/auth/exchange-legacy` | a token from the retiring backend | `invalid_legacy_token` (401), `legacy_account_not_imported` (401), `legacy_exchange_unavailable` (503). Deleted at decommission |
| POST | `/api/v1/auth/logout` | bearer | revokes the presented chain |
| POST | `/api/v1/auth/password-reset` | none | always 202; never reveals whether the email exists; `too_many_requests` (429) |
| POST | `/api/v1/auth/password-reset/confirm` | reset token | `invalid_reset_token` (400) |
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
