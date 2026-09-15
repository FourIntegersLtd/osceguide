# 0004. Platform-issued JWT with pluggable identity providers

Date: 2026-09-15
Status: accepted

## Context
b2c users logged in with a Flask cookie JWT or, for white-label tenants, via Clerk SSO; b2b users had a separate JWT carrying memberships and an active workspace. Admin rights on b2c were a hard-coded email list. Delegating everything to Clerk or Supabase Auth was considered: less code, but vendor lock-in on the most central table, and the frontend does not carry either SDK today.

## Decision
The platform owns `users` and issues its own short-lived access tokens (15 minutes) with rotating refresh tokens. Claims carry the user's memberships (`org_id`, `org_slug`, `role`, `surface`), the active workspace and a platform-admin flag, so authorisation needs no database read. Password login and external providers (Clerk first) implement one `IdentityProvider` protocol in the `identity` slice. Tokens are presented as `Authorization: Bearer`.

## Consequences
- One login for every product; workspace switching re-issues the token.
- Platform admin is a column on `users`, not an email list.
- Adding an identity provider is a new adapter, not a new auth system.
- The frontend stores the access token and refreshes it; cookies are not used for the API.
