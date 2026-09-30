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
cd backend/platform-api
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
  tests/security
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
  `backend/platform-api`, with the docker services up and migrated:
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
- `/login` asks `GET /api/v1/auth/sso/sign-in?host=localhost` and gets a 404
  locally; it shows in `problems` on every run and is known.
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
