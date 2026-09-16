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
- As **anyone**, I sign out so that my refresh token stops working.
- As **anyone**, I request a password reset and set a new password with the emailed token.
- As a **user provisioned by my institution**, I sign in with a temporary password and
  am told I must change it.
- As an **SSO user**, I sign in through my institution's provider and get the same
  platform token as everyone else.
- As **anyone**, I read my own profile and memberships.

## Aggregates & invariants
**User** is the aggregate root; credentials, external identities and refresh tokens
live inside it and are never addressed independently.

- `email` is unique, case-insensitive. The migration merges b2c's four `*_users`
  collections and `b2b_users` on the lowercased address.
- A password is stored only as an argon2id hash. No SHA-256, salted or otherwise.
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
| POST | `/api/v1/auth/login` | none | `invalid_credentials` (401), `account_suspended` (403) |
| POST | `/api/v1/auth/refresh` | refresh token | `invalid_refresh_token` (401) on reuse or expiry |
| POST | `/api/v1/auth/logout` | bearer | revokes the presented chain |
| POST | `/api/v1/auth/password-reset` | none | always 202; never reveals whether the email exists |
| POST | `/api/v1/auth/password-reset/confirm` | reset token | `invalid_reset_token` (400) |
| POST | `/api/v1/auth/change-password` | bearer | the only route allowed while `must_change_password` |
| GET | `/api/v1/me` | bearer | profile, memberships, active workspace |

## Jobs
`send_password_reset_email`, `send_welcome_email` — enqueued in the same transaction
as the row they concern.

## Cross-slice dependencies
None. `tenancy` reads users through this slice's service; this slice never reads
`tenancy`. Memberships reach the token because the login service asks `tenancy` for
them — the call goes downward, from `tenancy` into `identity`, never back.
