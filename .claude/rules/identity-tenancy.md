---
paths:
  - "api/app/features/{identity,sso,tenancy}/**"
  - "api/app/core/{auth,tenancy,memberships,role_policy,account_status}.py"
  - "api/tests/security/**"
  - "web/src/foundation/session/**"
  - "web/src/middleware.ts"
  - "web/src/app/(auth)/**"
  - "web/src/app/api/session/**"
---
# Identity and tenancy: what to know

Owner: `access-owner` (org admin and memberships inside `tenancy/` are `institution-owner`'s).
Proof: `verify-access`. Anything that touches auth is ask-first.

- Tokens and identity providers: ADR 0004. Entitlement is not payment: ADR 0012.
- A gate fails closed. A client branches on an `AppError` `code`, never on `message`.
- **Authorisation is the server's.** The browser calls `can(session, "manage_team")`
  against `/me/capabilities`; it never derives a permission from a role. Permission
  names are a union in `foundation/session/permissions.ts`, taken from
  `tenancy/service.py`. A new permission goes in both, never as a literal.
- `core/tenancy.py`'s `require_org` and the JWT reader decide who gets through; what an
  organisation does once inside is `institution-owner`'s.
- **`trainee_id` means two things.** Circuit slots use `users.id`; result decisions use
  `trainees.id`.
- Org-scoped repositories take the org id on every query (guard:
  `test_org_scoped_repositories.py`). A tenant-scoped change also runs `tests/security`.
- An invitation to an SSO-only organisation cannot be reissued as a password invite
  (`tests/security/test_sso_only_invitation_reissue.py`). SSO state is single-use.
- Temporary passwords for team invites and roster adds are decided (B-1): the first sign-in
  forces a change (`foundation/session/temporaryPassword.ts`, `(auth)/change-password`).
- `/api/session*` route handlers and `middleware.ts` are the browser session. CI was green
  while the app signed everyone out on reload: prove any change here in a signed-in browser
  (`web/.claude/skills/verify/features/session.md`).
- **Legacy b2c passwords.** `users.legacy_password_hash` (bcrypt, from the import) is accepted once in
  `login_with_memberships` and replaced by argon2id; `set_password_hash` and `set_temporary_password_hash`
  null it, so a reset kills the old password. `verify_password` never reads it. b2b SHA-256 is never
  imported. A test that signs in and then asserts on the fixture must `commit()` first: a refused
  request rolls `db_session` back and detaches what was only flushed.
- Open security findings: `api/docs/security/`.
- Every route's minimum role is derived from its dependencies (`core/openapi.py` `minimum_role`) and
  exported as `x-capability` (plus `x-platform-admin` on org rungs). No resolvable role: add it to
  `NO_ROLE` in `tests/guards/test_route_roles.py` with a reason (the list only shrinks). A stream that
  checks its role in the handler states it with `openapi_extra={"x-capability": ...}`; the guard
  refuses a stated role below the enforced one. A per-resource grant is a dependency marked
  `@grant("partner_reporter")` (`GRANTS`; growth's `PartnerReporter`), never a handler-side check.
  `require_org` returns an `OrgGate` whose `predicate.name` and `allow_platform_admin` the document
  reads. `tests/http/test_route_roles.py` sends the rung below.
- web `scripts/check-route-gates.mjs` fails a write whose screen checks no permission admitting the
  route's rung. A gate on the button (`AuthoringButton write`) is invisible to it: allow-list with why.
- Account-close and 2FA-off copy (`capabilities/account/settings/CloseAccount.tsx`, `TwoFactorPanel.tsx`): there are no Stripe subscriptions (A-34), so never say a subscription is cancelled; say paid access ends with the account, no refund. Each destructive step is `ConfirmModal`, with a success toast after 2FA-off.
- **One tab, many people.** `signOut(to = "/login")` sets `signedOutTo`, which `RequireSession` follows
  (no `next`; CloseAccount passes `/login?deleted=1`, never its own replace: it lost the race). After
  an expiry, `next` is followed only by the same person: `nextAfterSignIn` against `lastSessionUser()`
  (sessionStorage), in both `Login.land` and `RequireAnonymous`. The last workspace is per user id.
  The sign-out destination holds only on the page signed out from (`signedOutDestination`). After a
  sign-in, `refresh()` never joins a `/me` load started with the old tokens (`sessionLoads.after`).
  A surface's capability gate goes outside its shell. Journeys: CONSOLE-4, SWITCH-1..3.
- **An effect of signing in waits for the whole sign-in.** Reopening a closed account (undoes the
  closure and its erasure) runs where the session is minted (`service_mfa._issue_session`), never on
  the password alone; checks before the second factor use `can_reopen`, which writes nothing.

- **"May open" is not "holds".** `exam_access.codes` also carries the sign-up exam (a trial browses it); only `current` and the dashboard's `entitlements[live]` say what is held. The web keeps no exam of its own: the active exam is the server's `current_exam_code` (`resolveCurrentExam`), because a browser-remembered exam outlived the grant it was picked under and the marketplace then refused the person `not_entitled`. Screens that post an exam (marketplace, peer queue) are refused otherwise. Consumer surfaces resolve exams without an org on purpose (ADR 0017).

## What a failure looks like here
- A gate that fails open: missing, revoked or expired state lets someone in.
- A cross-tenant read or write: a query without the org id, or a token's memberships trusted past their truth.
- A reused or replayable token, link or SSO state; a password or session that survives the change meant to end it.
- Sign-out on reload, or the next person in the tab given the last person's page.
- Auth screens share `AuthShell`, `AuthFormField` and `AuthButton` (`.site-root.site-auth` page, header and navy quote panel around them). The card itself is the SignIn board's `.card.pad`: `AuthShell` sets `data-surface="assess"` on it so `boardKit` and `osce-*` tokens resolve inside the public-site page, 460px, `self-start`. `compact` is the board's 16px h2 state card; `hideLabel` is `sr-only` where the board has a placeholder only. Anything the app keeps and the board omits (password hint, eye, "Remembered it?") carries `data-auth-extra` so `e2e/assess/board-auth.spec.ts` can hide it. The MFA code stays one input (paste, autofill and its label depend on it); don't split it into digit boxes.
- The shared account screen (`capabilities/account/settings`) has two skins chosen by `useBoardSkin()` (org surface): `AccountCard` / `AccountButton` in `AccountKit.tsx` draw the Settings board's cards on assess, hire and partner, and the old `Panel` / `Button` for the trainee. Same behaviour, same handlers; add new account cards through `AccountCard`. `consoleDesign.test.ts` scans this folder: write `text-ink` / `text-ink-muted`, never `osce-ink-*`.

- **The opening exam is the oldest live grant, ties by id.** `entitlements.repository.for_user` orders by `(created_at, id)`; grants written in one transaction share `created_at`, and `exam_access.current` reads that order. A test that wants "first" and "second" grant sorts by `starts_at` itself. The web never falls back to `users.exam_code` (`resolveCurrentExam`): a null `current` means loading, failed or fail-closed, and screens ask nothing.

- **Password hashing is async.** `tokens.hash_password`, `verify_password`, `verify_legacy_password` and `verify_absent_password` run on a thread (`asyncio.to_thread`), so always `await` them; a sync call would stall every request. Tests and scripts that need a hash outside a loop use `tokens._hash_sync`.
- **The auth-status and org-active caches store only "active".** `core.account_status.refuse_if_deactivated` and `core.tenancy._refuse_if_org_inactive` cache the word "active" for `auth_status_cache_seconds` (30 s); any other status raises and is never stored, and Redis down reads the database. Platform admins read fresh (`fresh=principal.is_platform_admin`). Any new write to `users.status` or `organizations.status`/slug must call `forget_status` / `forget_org_active` (they drop the key after commit). Accepted bound: a read that began before an invalidation can write "active" back, so a deactivation can take up to 30 s to bite in that race.
- **Rate-limit counters are one Lua script** (INCR plus EXPIRE on first hit): never split into SET then INCR, which can leave a key with no TTL. `count_locally` applies with Redis off too. The sign-in ceiling per address is `SIGN_IN_ADDRESS` (setting `sign_in_per_address_per_minute`).
- **SSO callback uses short sessions.** `complete_callback` reads the arrangement, verifies with the broker with no connection open, then provisions in a second session (`SessionOpenerDep` on `POST /auth/sso/callback`).
- **An invitation token names its organisation.** `password_reset_tokens.organization_id` (null for a plain reset) is set by `invite_user`/`reissue_invitation`/`seat_or_invite` when the caller passes `organization_id`, and carried forward by the reminder job. `GET /auth/invitation/{token}` returns only `organisation_name`; every other token gets `invalid_reset_token`, under its own `INVITATION_LOOKUP` limit (fails closed). A new invitation caller must pass `organization_id`.
