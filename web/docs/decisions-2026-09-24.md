# Three decisions to close out the port — 2026-09-24

Everything else the 2026-09-24 audit found is built, verified, and sitting in
the working tree (`docs/parity-fix-plan.md` §8 has the full record). These
three are the only things actually waiting on you rather than on engineering
time. Answer each below, and the next session has nothing left to
investigate — only to build exactly what you chose.

---

## 1. Achievements — what is a streak, on this backend?

**Where it stands today:** the screen works and is reachable, but it computes
streaks and badges in the browser from your last 100 attempts. There is no
backend record of it — refresh from a different device and the "streak" is
recalculated from scratch, not read from anywhere durable. `platform-api` has
no achievements table, no streak concept; `attempts` is the only progress
record that exists.

**Why it's stuck on you, not engineering:** "streak" needs a definition
before it can be a database column. A streak of what — a day you did at
least one station? A week? Does a missed weekend break it? Does practice
count the same as a real exam sitting? None of that is a code question.

**Options:**

- **A — Leave it as a client-side approximation, but be honest about it.**
  Relabel the screen "Recent activity" instead of "Achievements," so it stops
  implying a persistent record it doesn't have. Cheapest, ships today.
- **B — Build a real backend record.** Needs the streak definition above,
  then a small `achievements`/`activity` table, a daily-rollup job or a
  read derived from `attempts` at query time (cheaper, no new table — just
  an indexed query over `attempts.created_at` per user). Half a day once the
  definition exists.
- **C — Drop it.** If nobody's asked for it since the port, it's a legal
  option too.

**Your answer:** B — build a real backend record. **Done 2026-09-24.**
`GET /me/achievements` (`app/features/dashboard/{router_achievements,service_achievements,schemas_achievements}.py`),
computed over the whole marked history via `attempts.service_reads.evaluated_for_user`
(bounded at 5,000 attempts, not paged at 100). Same streak definition as the
old client-side calculator, ported byte-for-byte and pinned with unit +
HTTP tests. `AchievementsLive.tsx` now calls it through `AsyncBoundary`
instead of computing in the browser; the dead client-side calculator
(`achievementsFromAttempts.ts`) is deleted.

---

## 2. SSO — two narrow gaps, not the whole feature

**Correction from what I told you earlier today:** SSO sign-in itself is
**already built**, not open. `POST /auth/sso/login` and `/auth/sso/callback`
work end to end through Clerk — backend (`app/features/sso/router.py`) and
frontend (`capabilities/account/Login.tsx`, `SsoCallback.tsx`) both call it.
I had stale information when I said otherwise; verified in source just now.

**What's actually still open, per `backend/platform-api/docs/OPEN-QUESTIONS.md` S-1:**

- **No Entra/OIDC adapter.** Only Clerk has one. An organisation configured
  for `provider: entra` is refused with `sso_provider_unsupported`. If every
  institution you're onboarding uses Clerk (or Clerk-brokered Microsoft),
  this doesn't matter. If any of them need direct OIDC to their own Entra
  tenant, it needs building.
- **`sso_only` is enforced weakly.** An SSO-provisioned account has no
  password hash, so password login fails for them today *by accident* (no
  hash to check against) rather than by an explicit refusal. If somebody on
  an `sso_only` org later sets a password some other way, nothing stops them
  logging in with it. This is a real, if narrow, security hardening gap —
  worth a one-line fix (check `sso_only` before attempting password verify)
  regardless of the Entra answer.

**Your answer — do you have or expect any Entra-only institutions in the near
term?** Yes. **Done 2026-09-24.**

- **Entra/OIDC adapter**: `app/features/sso/entra.py`, behind the same
  `SsoBroker` port Clerk already implements. One multi-tenant app
  registration (`ENTRA_CLIENT_ID`/`ENTRA_CLIENT_SECRET`) serves every
  institution; `organization_sso.issuer` carries each institution's own
  tenant id. Real authorization-code exchange plus signature verification
  against Entra's own JWKS (`aud`/`iss` checked, not just decoded) — nothing
  is trusted unverified. `service_login.SsoBrokers` now dispatches to
  whichever adapter an organisation's `provider` names, replacing the
  single hardcoded Clerk instance; `sign_in_url`/`verify` both take the
  org's `issuer` so one broker instance serves every tenant. 10 tests in
  `tests/http/test_sso_login_routes.py`, including one exercising the
  full Entra flow end to end against the fake broker.
- **`sso_only` password-login hardening**: `users.password_login_disabled`
  (migration `02a17a847052`), set once by
  `identity.service_sso.sign_in_external` when a person is provisioned or
  signed in against an `sso_only` arrangement — `identity` sits below `sso`
  in the layer contract and cannot check that configuration at login time,
  so the fact travels down at provision time instead, the same shape
  `catalog`/`roster`'s `RESTRICT`-catch pattern uses for a check they
  can't make upward. `POST /auth/login` now refuses with a distinct,
  honest `password_login_disabled` (not the account-enumeration-safe
  generic `invalid_credentials` — the org's SSO requirement is already
  public via discovery, so naming it here leaks nothing new) instead of
  accidentally failing on a missing hash. The forgot-password flow answers
  the same non-leaking 202 an unknown address gets and issues no token,
  so it can't become the back door. **Known residual gap, flagged in
  code**: `service_invitations.py`'s admin-initiated resend-invitation
  flow also mints password-reset tokens and does not yet check this flag —
  lower risk (admin-initiated, not self-service) but worth closing in a
  follow-up.

(The `sso_only` hardening fix doesn't need an answer from you — flagging it
as a recommended fix either way, low cost, do it next pass.)

---

## 3. GDPR erasure for a trainee with real exam history

**Where it stands today, as of this afternoon's work:** an institution can
now delete a trainee roster row outright — but **only** if nothing was ever
decided about them. The moment a real exam decision exists
(`candidate_result_revisions`), the delete is refused (`trainee_in_use`, 409)
and the admin is told to revoke access instead. This was a deliberate,
safety-first build: the underlying database constraint used to `CASCADE` on
trainee delete, which would have silently destroyed someone's exam decision
history the first time anyone tried it. That's fixed now regardless of your
answer below.

**The actual open question:** if a trainee **with** real exam history asks to
be forgotten — a genuine GDPR Article 17 request — there is currently no path
to that at all. Revoke access keeps the record; today's delete refuses
outright.

**Why it's not mine to decide:** this is a legal/compliance call about what
"erasure" has to mean for an exam result — can a decision record be
anonymised (address and name scrubbed, decision and rationale kept for audit)
rather than deleted outright? Does the retention obligation for exam records
override the erasure right, and for how long? That's a compliance-owned
answer, not a product or engineering one.

**Options once you have that answer:**

- **A — Anonymise, don't delete.** Scrub PII off the trainee row and any
  linked decision, keep the decision itself. Preserves audit trail, likely
  satisfies most erasure obligations for regulated exam records. Medium
  build — needs a defined "anonymised" state, probably its own audited
  action like the console's `delete-progress`.
- **B — True hard delete, cascading through decisions.** Simpler to build,
  loses the record entirely. Only appropriate if there's no retention
  obligation on the decision itself once the person is gone.
- **C — No self-service path; route every request through a human/manual
  process for now.** Zero build cost, but doesn't scale and isn't really an
  answer, just a deferral.

**Your answer — who owns this call, and what's the retention obligation on a
released exam decision?** A — anonymise, don't delete. **Done 2026-09-24.**

`POST /orgs/{org_slug}/trainees/{trainee_id}/anonymise` — scrubs
`email`/`first_name`/`last_name`, revokes access, and marks
`trainees.anonymised_at` (migration `2b982c151fdf`). The decision itself
(`candidate_result_revisions`) is never touched — this is the whole point,
and it's why it's offered unconditionally rather than only for a row
`DELETE` would refuse: scrubbing a name never needs the `RESTRICT`'s
protection, so there's no reason to gate it the way delete is gated.
Idempotent (a repeat call is a no-op, still answers 200, writes no second
audit row) and audited on the organisation's own log
(`tenancy.service_audit.record_for_org`, a new org-scoped twin of the
platform-only `record` that already existed). 4 tests in
`test_roster_edit_routes.py`. Frontend: an "Anonymise" button beside
Delete in the roster table, with its own confirm dialog and a disabled
"Already anonymised" state once done.

---

## Once these are answered

Each decision above is scoped small enough that the build is a day or less
per item once you've answered. Nothing else from the 2026-09-24 audit or the
original port plan needs a decision — everything else is either done, or was
confirmed a non-gap (see `docs/parity-fix-plan.md` for the full trail).
