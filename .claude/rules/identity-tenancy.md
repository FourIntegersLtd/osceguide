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
