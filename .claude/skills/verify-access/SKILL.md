---
name: verify-access
description: How to prove a change to access works — sign-in, sessions, SSO, invitations, entitlements, Stripe billing, referrals and the email outbox, across platform-api and platform-web's session and account code. Use before calling any access change done.
---

# Verify access

Pick the **lowest level that can see your change**, run it, and report the
command and its output. Anything a signed-in browser does is Level 2: CI was
green while the app signed everyone out on reload.

| Your change | Minimum proof |
|---|---|
| An entitlement, billing, growth or notification rule | Level 1, and show the rule is called |
| Tokens, a guard in `core`, a role or permission | Level 1 including `tests/security` |
| Sign-in, sign-out, sessions, cookies, middleware, SSO | Level 1 + Level 2 |
| Invitations, password reset, anything that sends email | Level 1 + read the outbox row |
| The Stripe webhook or checkout | Level 1; say plainly that no live webhook was sent |
| Account closure, erasure or `/me/export` | Level 1 including `tests/http/test_identity_routes.py`; for erasure, also run it once against the local DB (see Traps) |

## Level 1 — backend tests (~2.5 min, needs the docker services)

```bash
cd api
docker compose up -d            # Postgres :5433, Redis :6380; without them DB tests skip
poetry run pytest -q \
  tests/unit/test_auth.py tests/unit/test_identity_domain.py tests/unit/test_mfa_domain.py \
  tests/http/test_mfa_routes.py \
  tests/unit/test_jwt_claims_oracle.py tests/unit/test_legacy_exchange_domain.py \
  tests/unit/test_sso_domain.py tests/unit/test_entitlements_domain.py \
  tests/unit/test_entitlement_exam_access.py tests/unit/test_billing_domain.py \
  tests/unit/test_stripe_signature.py tests/unit/test_growth_domain.py \
  tests/unit/test_receipt_document.py tests/unit/test_receipt_oracle.py \
  tests/unit/test_notifications_domain.py \
  tests/repository/test_identity_repository.py tests/repository/test_notifications_outbox.py \
  tests/http/test_identity_routes.py tests/http/test_sso_routes.py \
  tests/http/test_sso_login_routes.py tests/http/test_entitlements_routes.py \
  tests/http/test_platform_entitlement_routes.py tests/http/test_billing_routes.py \
  tests/http/test_platform_billing_routes.py tests/http/test_growth_routes.py \
  tests/http/test_legacy_exchange_routes.py tests/http/test_invitations.py \
  tests/security tests/http/test_platform_ops_routes.py tests/unit/test_rate_limit.py
```

390 passed on 2026-09-26 (was 354 on 2026-09-25; the growth and identity suites
grew with A1-A4, the retiring client's Settings-screen parity work: encrypted
bank details for referral payouts, `/me/referrals/history`, the custom
reading/simulation timers, and `exam_time`). Frontend session code: `cd
platform-web && npm run ci` (the `foundation/session` unit tests are in it).

## Level 2 — a real browser session

Use platform-web's `verify` skill: `doctor.mjs` until `ready`, then drive
`features/session.md` — signed-out redirect, sign in, **reload**, sign out.
The reload is the check that matters. Use only `@example.com` accounts; the
local database holds imported real users.

The Stripe CLI is installed on this machine. `stripe listen --forward-to
localhost:8002/api/v1/billing/webhooks/stripe`, with the secret it prints as
`STRIPE_WEBHOOK_SECRET`, would deliver a real test-mode event. Nobody has run
it here yet; the first owner who does writes the steps into this file.

For email: trigger the flow, then read the `notifications` outbox row it
queued. No `RESEND_API_KEY` locally means nothing is sent, which is correct.

## Traps

- The sign-in e2e needs Docker running and `walkthrough@example.com` bootstrapped with an `ADMIN_TOTP_SECRET` and its `must_change_password` flag cleared, plus seeded station templates. The cookie modal blocks clicks until "Continue without analytics".

- **A legacy sign-in is consumed by the first thing that verifies it.** A legacy b2c password is
  accepted once and replaced with argon2id (`service_sessions.login_with_memberships`), so the web
  harness's `signIn`, which probes the login API before driving the form, spends the upgrade and the
  form then proves nothing. Prove a legacy sign-in with a form-driven script, and re-seed the legacy
  hash between attempts.
- **Port 8002 may already be held by another session's API stub.** `make start` then binds nothing
  and the browser talks to the other session's process. Start the proof API on a free port and point
  web at it, rather than reclaiming 8002.
- **The onboarding dialog hides sign-out until the proof user has an `exam_code`.** Set one on the
  row before proving anything that needs a sign-out and a second sign-in.
- **Read the skip count, not just the exit code.** `tests/http/test_mfa_routes.py` is skipped whole while
  two-factor sign-in is switched off (`service_mfa.finish_password_sign_in`): 15 skips in Level 1 is
  that. A run with dozens more skipped exited 0 because Postgres was unreachable at session start on
  a loaded machine (2026-10-18); rerun with `-rs` and check every skip reason is the MFA one.
- **Closed-account reopen happens at session mint** (`service_mfa._issue_session`), not on the
  password. Prove a reopen change on both `/auth/login` and `/auth/mfa/verify`; the MFA path needs a
  challenge minted with `tokens.issue_mfa_challenge` while the gate is off
  (`tests/http/test_identity_routes.py::_closed_with_authenticator`).
- **`$TMPDIR` is shared with other sessions on this machine.** A `make ci > "$TMPDIR/ci.txt"` was
  overwritten mid-run by another session's web lint (2026-10-11). Write proof output to the
  session scratchpad instead.
- **The request session commits before the answer only with `scope="function"`.** FastAPI exits a
  default-scope `yield` dependency after the response is sent, so a 201 from register reached the
  e2e setup before the commit and the next seat 500'd on `uq_users_email` (2026-10-11). Every
  `Depends(get_session, ...)` says `scope="function"`; `tests/guards/test_commit_before_response.py`
  fails otherwise. The in-process `client` cannot show the ordering (it waits for the whole app and
  shares one transaction): that guard drives the real `get_session` and records commit vs last byte.
- **A password change or reset revokes every chain, the current one too.**
  Change-password answers a fresh pair that the web adopts (A-13); a reset
  answers none, so `/reset-password` signs the browser out before showing
  done (A-10). A screen that skips either leaves cookies the backend refuses:
  `/login` bounces to `/app` and every call there answers 401. Other devices
  keep their access token, so they drop within 15 minutes, not at once.
- **A refused refresh is checked back before the cookies go.**
  `/api/session/token` answers `{access_token: null, refused: <fingerprint>}`
  and clears only when the client's second ask still carries that token, so a
  pair another tab stored meanwhile survives. Proof:
  `src/app/api/session/token/route.test.ts` (the loader resolves `next/*`).
- **SSO discovery throws.** `readSsoSignIn` no longer folds a failure into
  `null` (A-5); a caller that can tolerate a miss catches it itself.
- **Abandoned mail is on the System health page** (S-5): `GET
  /platform/outbox/undelivered` lists outbox rows that failed twelve tries and
  `POST /platform/outbox/{id}/retry` re-queues one. Prove it with the stored
  row, not the panel alone.

- **Erasure and export must reach other slices only through `service*`
  modules.** `identity/service_erasure.py` and `identity/service_export.py`
  (E-4, E-5, landed 2026-09-27) call `attempts.service_privacy`,
  `billing.service_receipts.export_payments_for_user` and
  `tutor_memory.service.forget_everything` — never another slice's
  `.models`/`.repository`. `test_slices_call_services_only` and
  `test_sql_lives_in_repositories` catch a direct import immediately; the fix
  each time is a new `service_privacy.py`/`service_*` function in the *owning*
  slice, not a query in identity.
- **Proving the erasure job needs a plain script, not just pytest.** From
  `api`, with the docker services up and migrated:
  `PYTHONPATH=. poetry run python <script>` that creates a user, closes it,
  backdates `closed_at` (`repository.user_by_id` then set the attribute and
  commit), calls `service_erasure.erase_due_accounts(session, now=...)`, and
  reads the row back. A bare `poetry run python` from outside pytest cannot
  import `app` without `PYTHONPATH=.` — this is not a code bug.
- **Entitlement grants are not live grants.** `entitlements.list_for_user`
  returns revoked and expired rows. A gate must filter on `live` and fail closed.
- **The consumer cookie blocks the auth bridge.** It is httpOnly and
  host-only; the institution arm's bridge works, the consumer arm's needs a
  product decision. Do not "fix" it by loosening the cookie.
- A platform admin reads any organisation for support but holds none of its
  powers (`OrgAdmin` is `allow_platform_admin=False`). A 403 there is correct.
- `/login` asks `GET /api/v1/auth/sso/sign-in?host=<host>`; a host with no SSO
  answers 200 `null` (since 2026-10-03; before that a 404 showed in `problems`
  on every run). A 404 there now is a stale api.
- `GET /api/v1/me/referral-payout-details` answers 200 `null` when nothing is
  saved (since 2026-10-06; it was a 404 in `problems` on staff settings).
- Staff settings (`/staff/settings`) are Account / Security / Data; consumer
  settings (`/app/me/settings`) keep Profile / Preferences / Payments / Referrals /
  Memory (Exam left on 2026-10-11; `?tab=exam` falls back to Profile, which shows the exam type). Prove both when touching `capabilities/account/Settings.tsx`.
- Onboarding voice starts only on "Play Athena's introduction". Prove it with a
  fresh `@example.com` account registered with `exam_code` (lands on the
  onboarding dialog) and count `POST /assistant/sessions` before play: 0
  (`web/.verify/fix-B16.mjs`). Never press play in a proof: it is billed.
- Directory tiles (`paid`, `trial`) are whole-directory counts and match the
  Paid / On trial filters; the per-exam cards miss payers with no exam set.
- Hydrate `/login` before submitting (the harness's `signIn` does). Submitting
  the server HTML posts as a GET and looks exactly like a session bug.
- Checkout grants nothing; only the webhook does. A paid user with no access
  means look at `GET /api/v1/platform/users/{id}/billing-events`.
- **A repository function that mutates a `Timestamps` row must `session.refresh()`
  before returning it if the caller reads `updated_at`.** `onupdate=func.now()`
  is evaluated by Postgres, so the Python object is left expired after the
  `UPDATE`; reading the expired attribute outside the request's async context
  raises `MissingGreenlet`, not a clear error. Caught in
  `growth.repository.upsert_payout_details`'s update branch (2026-09-26): the
  create branch refreshed, the update branch didn't, and only a real PUT-then-PUT
  test caught it — the round-trip GET test alone did not.
- **A set-password refusal is not always about the link.** `password-reset/confirm`
  checks the password before the token, so a weak password on a good link answers
  `weak_password`, and a sixth try in five minutes `too_many_requests`. The reset
  and invitation screens once said "that link is no longer valid" for every error,
  sending people for a new link that failed the same way (B37). Only
  `invalid_reset_token` is a dead link: `mapResetPasswordError` in
  `capabilities/account/support/mapAuthApiError.ts`. The browser walk of both
  journeys, including spent and expired links, is in the platform-web `verify`
  skill's `features/session.md`.
- **Accepting an invitation signs the person in (B8).** `password-reset/confirm`
  answers `{"status": "accepted", "email": ...}` (pinned in
  `tests/http/test_invitations.py`). `ResetPassword` with `invitation` then calls
  the ordinary `login(email, password)` and goes to `/app`; an MFA challenge or a
  failed sign-in leaves the "Sign in" button. A plain reset deliberately still
  ends on the sign-in screen (it just revoked every session). Browser proof: seat
  an `@example.com` address from the staff console, take the token from the
  outbox row, open `/accept-invitation?token=...`, set a password, and expect to
  land signed in on `/app` (then reload: still signed in).
- **Settings account screens in a browser (A-27..A-33).** `walkthrough@example.com` is a
  platform admin, so Delete account is disabled and 2FA is mandatory there: register a fresh
  `@example.com` account (`POST /auth/register`, then `PATCH /me {"exam_code":"sca"}`) and
  drive that. Enrolling 2FA from a script: read `secret` off the `POST /me/mfa/enrol` response
  and compute the TOTP with `crypto` HMAC-SHA1. The server rejects a code reused in the same
  30 s step, so wait 31 s between the enrol code and the turn-off code or the turn-off looks
  broken. Walk Delete account to the second confirm and cancel; never confirm it.
  Scope delete-flow locators to `getByRole("dialog")` (the page's first textbox is Username);
  the second confirm cancels with "Back", then "Keep account".
- **Payments and checkout (A-38..A-40).** Local checkout answers 503 (no Stripe key): that proves
  only the failure path (blank tab opened, then closed, error shown). For the success and
  blocked-popup paths, stub `**/billing/checkout` with `page.route` returning a `checkout_url`
  and read the new tab from `context.waitForEvent("page")`; say the checkout was stubbed. Payments
  re-reads `/me/entitlements` on `visibilitychange`: count those requests. Trial account: insert a
  `trial` entitlement for a fresh `@example.com` user; paid: an account with a live purchase.
- **Board-diff of sign-in screens.** `e2e/assess/board-auth.spec.ts` scores Sign in, Forgot, Reset, Accept invitation and Register organisation at 1440 and 760 against the boards; Your account is `board-settings.spec.ts`. The invitation page needs a real token: `seedInvitationToken` adds a person to the org and reads `payload->>'token'` from `outbound_messages`. Set `localStorage` `analytics-consent` and `installPromptDismissed` in the app context or the cookie and install prompts cover the card. A shared dev server dies with 500 when another lane leaves a file unparsable (`tsc` shows it): wait or ask, do not fix their file.
- **Preferences save per switch.** Count `PATCH /me` bodies: each switch sends only its own field,
  extra time sends the timers on confirm, then reload and check the switches persisted.
- **Trial window (peer practice, marketplace).** A trial holds no entitlement row, so age the
  user instead: `UPDATE users SET created_at = now() - interval '15 days', activated_at = NULL`.
  Then queue/offer/claim/join/voice-token must answer 403 `not_entitled` with `details.reason`
  `trial_expired`, while a 3x3-exhausted trial inside 14 days still peers. Proof:
  `poetry run pytest tests/http/test_entitlements_trial_window.py`. One failing request per test:
  the 403 rolls back the shared `db_session`.
- **`make ci` runs the guards after the unit tests, and they bite auth code.** `test_sql_lives_in_repositories` flags any `.execute(` outside a repository (a Redis pipeline's `execute` too: use a Lua `eval`); `test_code_is_documented` wants a sentence on every nested function; `test_ownership` needs a new test file to match an OWNERS glob (`tests/http/test_identity_*`); `test_services_never_commit` forbids `session.commit()` in a service (the conftest savepoint session hides it, the real `get_session` raises). A cache test must wrap the `get_session` override to also run `cache.flush_cache_ops`, as the conftest does not.
