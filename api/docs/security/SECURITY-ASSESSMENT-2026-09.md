# OSCE Guide Platform — Security Assessment Report

| | |
|---|---|
| **Report title** | Security Assessment of the OSCE Guide Platform (platform-api, platform-web, assessment-platform) |
| **Version** | 1.2 (2026-09-25 remediation pass: SEC-008/009/010/014/015/016 fixed with regression tests) |
| **Assessment type** | Internal white-box security assessment / penetration test (local environment) |
| **Assessment dates** | 2026-09-24 – 2026-09-25 (incl. a deep-dive verification round on 2026-09-25) |
| **Report date** | 2026-09-25 |
| **Assessor** | OSCE Guide internal security assessment |
| **Classification** | **CONFIDENTIAL** — restricted distribution |
| **Standards** | OWASP WSTG v4.2, OWASP ASVS 4.0.3 L2, OWASP API Top 10 (2023), OWASP LLM Top 10 (2025), CIS Docker/Kubernetes, CVSS 3.1 |

> **Confidentiality notice.** This document describes security weaknesses in a
> live system and is confidential. Distribute only to those with a need to know.
> All credentials and secrets referenced have been redacted.

> **Note on scope.** This is round one: a **local, white-box** assessment of the
> new stack before it takes production traffic. Production is a separate
> follow-on engagement (v2). See `PENTEST-PLAN.md` for full rules of engagement.

---

## 1. Executive summary

OSCE Guide commissioned an internal security assessment of its new platform —
the FastAPI backend (**platform-api**), the Next.js 16 web application
(**platform-web**), and the LiveKit voice workers (**assessment-platform**) —
ahead of cutover from the legacy stack and ahead of institutional customer due
diligence.

The assessment was white-box (full source access) and mapped to the same
standards an accredited third-party firm would use (OWASP WSTG/ASVS L2, API Top
10, LLM Top 10, CIS benchmarks, CVSS 3.1). Every confirmed issue was captured as
an automated regression test so that fixes are provable and durable.

**Overall risk rating: MEDIUM.** The platform's core security architecture is
sound — token handling, password storage, tenant isolation and database access
are well built and, in several places, notably careful. No Critical issues and
no unauthenticated remote code execution were found. The findings are two
application-level High issues (both **fixed during this engagement**, each with
a regression test), one High credential-hygiene issue that requires an owner
decision to rotate secrets, and a cluster of Medium hardening items typical of a
pre-production platform.

A second, deeper verification round on 2026-09-25 (v1.1) widened coverage across
injection classes beyond XSS/SQLi (SSRF, deserialization, path traversal,
command/template injection, XXE, ReDoS), the full authentication lifecycle,
object-level authorization and mass-assignment, CSRF, payment integrity, and
voice-token authorization. It **cleared six whole vulnerability classes as
absent**, confirmed the payment and voice-token paths secure, corrected one
earlier finding (SEC-011 is already mitigated in code), and surfaced six new
lower-impact items (SEC-015 to SEC-020), two of which were fixed on the spot.

A remediation pass on 2026-09-25 then closed the backlog's fixable items, each
with a regression test: the voice session-length cap (SEC-008), the platform-api
container hardening and `.dockerignore` (SEC-009), the worker pod hardening and
NetworkPolicy (SEC-010), the circuit-enrolment roster lock-down (SEC-014, on the
owner's decision), and the Entra SSO `state`/`nonce` and stream-ticket single-use
controls (SEC-015, SEC-016). What remains open is the rate-limit hardening
(SEC-003/004), server-side validation of assistant `extras` (SEC-007), the
enforcing CSP (SEC-006, deferred pending a browser walk-through), upload content
sniffing (SEC-013), and the two owner actions — secret rotation (SEC-012) and the
reliability/informational items (SEC-017, SEC-020).

### Findings by severity

| Severity | Count | Fixed in this engagement | Open / owner action | Mitigated / informational |
|---|---|---|---|---|
| Critical | 0 | – | – | – |
| High | 3 | 2 | 1 | – |
| Medium | 8 | 4 (SEC-008, SEC-009, SEC-015, SEC-018) | 3 | 1 (SEC-006, partially mitigated) |
| Low | 7 | 5 (SEC-005, SEC-010, SEC-014, SEC-016, SEC-019) | 1 (SEC-013) | 1 (SEC-011, already mitigated) |
| Informational | 2 | – | – | 2 (SEC-017, SEC-020) |
| **Total** | **20** | **5** | **12** | **3** |

### Top issues for leadership

1. **Privilege escalation between organisation roles (High — FIXED).** A
   "partner admin" (a role meant for a practice/marketing surface that must
   never run an examination) could promote itself or any member to
   `institution_admin` or `owner` — the roles that sign off candidate results —
   because the role field accepted any string with no allow-list. In an
   examination product this crosses the integrity boundary that matters most.
   Fixed: roles are now validated against an allow-list and a granter can never
   grant above its own tier. Regression test added.

2. **Cross-context script execution via unsanitised content (High — FIXED).**
   The web app rendered markdown (including raw HTML) straight into the page
   with no sanitiser. The content it renders includes station text authored by
   organisation staff, help articles, and **the AI tutor's own chat replies** —
   so a lower-trust author, or a manipulated model, could have run JavaScript in
   another user's browser (session theft, actions as the victim). Fixed: a
   sanitiser now strips scripts, event handlers and dangerous URLs. Regression
   tests added.

3. **Secrets present in repository history and on disk (High — OWNER ACTION).**
   The backend git history contains private keys and an access token is embedded
   in a git remote URL; a Google Cloud service-account key sits in the working
   tree. These must be **rotated** (not merely deleted) as they may be live. This
   is the one High item that needs an owner decision rather than a code fix.

The remaining Medium/Low items are hardening: rate-limiting robustness, an
enforcing browser Content-Security-Policy, LLM cost/abuse caps, container and
Kubernetes hardening, and an SSO-only account edge case. None is independently
exploitable for a full compromise; together they raise the platform's baseline.

**Bottom line for a client auditor:** the platform is built on sound security
foundations, the two most serious application flaws were found and fixed with
tests during the assessment, and a clear, prioritised remediation roadmap
covers the rest.

---

## 2. Scope & method

### 2.1 Components and versions

| Component | Description | Path | Commit |
|---|---|---|---|
| platform-api | FastAPI backend, ~370 routes across ~59 routers; JWT auth; PostgreSQL | `backend/platform-api` | `b68dc7f` (`main`) |
| platform-web | Next.js 16 App Router; BFF refresh cookie + in-memory access token | `platform-web` | `6b62e611` |
| assessment-platform | LiveKit assessment + assistant voice workers on K3s | `assessment-platform` | `39692ae` |

### 2.2 Method

White-box. Route inventory taken from `/openapi.json`. Manual code review and
targeted dynamic tests against an **isolated** local instance (dedicated
database, dummy secrets, a separate port — the shared dev stack was untouched).
Every confirmed finding is encoded as a regression test.

### 2.3 In / out of scope

**In:** the three components above; auth, tenancy/authorization, payments &
entitlements, voice/worker endpoints, content injection, configuration.
**Out:** LiveKit Cloud SFU, Stripe infrastructure (test mode only; webhook
verification in scope), production environment (v2), DoS/load testing, retired
legacy apps (noted only where their artefacts affect the new repos).

### 2.4 Standards mapping

OWASP WSTG v4.2 (test cases), ASVS 4.0.3 **Level 2** (control baseline), API
Security Top 10 2023, LLM Top 10 2025, CIS Docker/Kubernetes, CVSS 3.1
(scoring). See the coverage checklist in Appendix A.

---

## 3. Risk rating method

Each finding carries a **CVSS 3.1 base score** with its vector string, then a
contextual severity that accounts for reachability in *this* system (who can
reach the entry point, and what trust boundary it crosses). Bands: Critical
9.0–10.0, High 7.0–8.9, Medium 4.0–6.9, Low 0.1–3.9.

---

## 4. Findings summary

| ID | Title | Severity | CVSS | Component | Status |
|---|---|---|---|---|---|
| SEC-001 | Org-role privilege escalation via unvalidated `role` | **High** | 8.1 | platform-api | **Fixed** |
| SEC-002 | Stored / model-driven XSS via unsanitised markdown | **High** | 7.6 | platform-web | **Fixed** |
| SEC-012 | Secrets in git history & working tree (keys, token, GCP key) | **High** | 7.5 | repos | **Open — owner action** |
| SEC-003 | Rate-limit key spoofable (XFF) and fails open | Medium | 5.3 | platform-api | Open — backlog |
| SEC-004 | No rate limit on registration / growth endpoints | Medium | 5.3 | platform-api | Open — backlog |
| SEC-006 | No enforcing Content-Security-Policy on web app | Medium | 4.7 | platform-web | Partially mitigated |
| SEC-007 | Unvalidated assistant `extras` → prompt steering & cost | Medium | 5.4 | platform-api | Open — backlog |
| SEC-008 | No cap on voice session length → LLM/voice cost abuse | Medium | 5.3 | assessment-platform | **Fixed** |
| SEC-009 | Container runs as root; build-ARG token in image history | Medium | 5.9 | platform-api | **Fixed** |
| SEC-015 | Entra SSO builds authorize URL with no `state`; no id_token `nonce` | Medium | 5.4 | platform-api | **Fixed** |
| SEC-018 | Slide renderer path traversal via LLM-generated `image_urls` | Medium | 5.0 | platform-api | **Fixed** |
| SEC-005 | Missing security headers; `/openapi.json` served when deployed | Low | 3.7 | platform-api | **Fixed** |
| SEC-019 | Clerk session id spliced unescaped into outbound API URL | Low | 3.1 | platform-api | **Fixed** |
| SEC-010 | Worker pods lack securityContext / NetworkPolicy | Low | 4.0 | assessment-platform | **Fixed** |
| SEC-013 | Station photo upload validates extension only (no content sniff) | Low | 3.1 | platform-api | Open — backlog |
| SEC-014 | Org may enrol an un-rostered arbitrary user id into a circuit | Low | 3.5 | platform-api | **Fixed** |
| SEC-016 | Stream/voice ticket is time-bound but not single-use | Low | 2.6 | platform-api | **Fixed** |
| SEC-011 | Password reset on SSO-only accounts | Low | 5.4→2.0 | platform-api | **Mitigated** (already blocked in code) |
| SEC-017 | Stripe checkout omits `metadata.price_id` webhooks depend on | Info | – | platform-api | Open — reliability |
| SEC-020 | Community `set_like` skips an audience visibility check | Info | – | platform-api | Open — cosmetic |

---

## 5. Detailed findings

### SEC-001 — Organisation-role privilege escalation via unvalidated `role` (High, FIXED)

- **CVSS 3.1:** 8.1 — `AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N`
- **Category:** OWASP API1:2023 Broken Object Level Authorization / API5 Broken
  Function Level Authorization; ASVS V4 (access control).
- **Component / location:** `app/features/tenancy/schemas.py` (role was
  `str, min_length=1, max_length=32`, no allow-list);
  `app/features/tenancy/service_memberships.py` (`add_membership`,
  `change_membership_role` wrote the role verbatim); routes
  `POST /api/v1/orgs/{slug}/memberships`, `PATCH …/memberships/{id}`, and the
  bulk add.

**Description.** Membership create/update routes are gated by the `OrgAdmin`
dependency, which — correctly for most operations — admits `partner_admin`. But
the `role` value on the request body was an unconstrained string written
straight to the database. The tenancy domain deliberately separates
`ORG_ADMIN_ROLES` (may administer) from `INSTITUTION_ADMIN_ROLES` (may sign off
and release a candidate's result); `partner_admin` is in the former and *not*
the latter, by design ("A partner admin runs a practice surface and never an
examination"). Because the role string was never checked, a `partner_admin`
could set its own role — or a new member's — to `institution_admin` or `owner`,
crossing exactly that boundary, or to an arbitrary undefined string.

**Impact.** Vertical privilege escalation to examination-signing authority
within an organisation. In an assessment product, this is an integrity issue of
the first order: it lets an actor who should only run practice reach the controls
that release official results.

**Evidence (regression test).**
`tests/security/test_membership_role_escalation.py`
- `test_partner_admin_cannot_grant_institution_admin` — before the fix the PATCH
  returned `201` (grant accepted); it must be `403`.
- `test_role_must_be_a_known_value` — before the fix `role:"superuser"` returned
  `201`; it must be `400/422`.
Both failed on the vulnerable code and pass after the fix. Full security suite:
`10 passed`.

**Remediation (applied).**
- `app/features/tenancy/domain.py`: added `GRANTABLE_ROLES` (an allow-list),
  `_ROLE_RANK`, and predicates `is_known_role`, `role_rank`, `may_grant_role`.
- `app/features/tenancy/service_memberships.py`: a `_guard_role_grant(actor,
  org_id, role)` helper now runs before every membership write — an unknown role
  is `InvalidInput` (422), a known role above the granter's own tier is
  `Forbidden` (403). Platform admins (acting from outside the org) may set any
  known role. This covers create, update and bulk add (bulk routes through
  `add_membership`).

**Reference.** OWASP API5:2023; CWE-269 Improper Privilege Management.

---

### SEC-002 — Stored / model-driven XSS via unsanitised markdown (High, FIXED)

- **CVSS 3.1:** 7.6 — `AV:N/AC:L/PR:L/UI:R/S:C/C:H/I:L/A:N`
- **Category:** OWASP A03:2021 Injection (XSS); WSTG-CLNT-01; **OWASP LLM Top 10
  — LLM02 Insecure Output Handling**.
- **Component / location:** `platform-web/src/foundation/ui/MarkdownRenderer.tsx`
  — the pipeline `remark().use(remarkRehype, {allowDangerousHtml:true})
  .use(rehypeRaw).use(rehypeStringify)` then `dangerouslySetInnerHTML`, with **no
  sanitiser**. The error fallback also injected raw `content` verbatim.

**Description.** `rehypeRaw` parses embedded raw HTML, and the result was written
straight into the DOM. Any `<script>`, `onerror=` handler, or `javascript:` URL
in the source string executed in the viewer's session. The renderer's inputs are
lower-trust: ortho station content authored by organisation staff, help
articles, media prose, and — most importantly — **the AI tutor's own chat
replies**. The last of these makes it an *insecure LLM output handling* issue:
content the model emits (which a candidate can steer via prompt injection) was
rendered as live HTML.

**Impact.** Stored/model-driven XSS: session compromise, actions performed as the
victim (including staff), and data theft in the victim's authenticated context.
Rated with UI:R (the victim must view the content) and scope-changed (the payload
runs in the victim's browser context).

*Note:* the community feature, another writer into this renderer, is not yet
surfaced in platform-web, so that particular chain is latent; the station /
help-article / AI-reply chains are live. The fix closes all of them.

**Evidence (regression test).**
`platform-web/src/foundation/ui/renderMarkdown.test.ts` — 7 tests: `<script>`,
`onerror`, `javascript:` links and `<iframe>` are stripped; ordinary formatting,
safe links and code-block language classes still render; `escapeHtml` neutralises
markup. `7 pass`. TypeScript `tsc --noEmit` clean.

**Remediation (applied).**
- Added the `rehype-sanitize` dependency (from the same unified/rehype ecosystem
  already in use) and inserted it after `rehypeRaw` with rehype's GitHub-derived
  default schema (no `script`/`style`, no `on*` handlers, no `javascript:` URLs,
  no `<iframe>`/`<object>`; keeps formatting and `language-*` code classes).
- Extracted the pipeline into `renderMarkdown.ts` so the security-critical code
  is unit-tested without a DOM, and changed the error fallback to render
  **escaped text**, never raw HTML (the old fallback reopened the sink on any
  pipeline error).

**Reference.** OWASP LLM02:2025; CWE-79.

---

### SEC-012 — Secrets in git history and working tree (High, OPEN — OWNER ACTION)

- **CVSS 3.1:** 7.5 — `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N` (assuming a live
  secret; drops to Low if all are already rotated/inactive).
- **Category:** OWASP A07:2021; WSTG-CONF-04; CIS secret management.

**Description.** The secret scan (Gitleaks) and manual review found:
- **`backend/.git/config`** contains an access token embedded in the remote URL
  (`https://<token>@github.com/FourIntegersLtd/OSCEGuide-backend.git`).
- The **backend git history** contains private-key files:
  `cloudflaressl.key`, `cloudflaressl.pem`, `osceguide.pem` (TLS private keys).
- A **Google Cloud service-account key** (`serviceAccountKey.json`, project
  `sca-buddy`, containing a `private_key`) is present in the working tree at the
  repo root.

(The web/legacy scan hits in `frontend/src/b2b/**` and `src/app/**` were reviewed
and are variable-name false positives, not live secrets.)

**Impact.** If any of these secrets is still valid, an attacker who obtains the
repository or a developer machine gains: repository push access (token), the
ability to impersonate the TLS certificate (private keys), or access to GCP
resources under the service account. Deleting the files is **not** sufficient —
history and any prior clones retain them.

**Remediation (requires owner decision).**
1. **Rotate** every secret listed: reissue the GitHub token, re-key/re-issue the
   TLS certificates, and create a new GCP service-account key (disable the old).
2. Move `serviceAccountKey.json` out of the tree; load it from a secret manager
   or an untracked path; ensure it is git-ignored everywhere.
3. Replace the tokenised git remote with SSH or a credential helper.
4. Consider history rewrite (e.g. `git filter-repo`) after rotation, and enable
   push-protection/secret-scanning on the remote.

**Reference.** CWE-798 Use of Hard-coded Credentials; CWE-540.

> This is the one High finding left open by design: it is a credential-rotation
> decision for the owner, not a code change the assessment should make unilaterally.

---

### SEC-003 — Rate-limit key is spoofable and the limiter fails open (Medium, OPEN)

- **CVSS 3.1:** 5.3 — `AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N`
- **Location:** `app/core/rate_limit.py` — `caller_key()` takes the first
  `X-Forwarded-For` value (spoofable by a direct caller), and `check()` lets
  requests through when Redis is unavailable.

**Description.** Brute-force and credential-stuffing protection on login and
password-reset depends on counting per caller. The caller key is taken from a
client-supplied header, so an attacker who can set `X-Forwarded-For` gets a fresh
bucket per request; and if Redis is down the limiter fails **open**, removing the
protection entirely. The code comment is candid that this "raises the cost of an
attack rather than preventing one."

**Impact.** Weakened brute-force protection on authentication endpoints.
Contingent on whether the production proxy overwrites `X-Forwarded-For` (verify
in the v2 production engagement).

**Remediation.** Trust `X-Forwarded-For` only for the known proxy hop (use the
right-most untrusted address, or a platform-provided trusted client IP); for the
**auth-specific** limits, fail closed (refuse) when the backing store is
unavailable, with a tight allowance so a store outage doesn't lock out all users.
Confirm the edge proxy strips inbound `X-Forwarded-For`.

**Reference.** OWASP API4:2023; WSTG-ATHN-03; CWE-307.

---

### SEC-004 — No rate limit on registration / growth endpoints (Medium, OPEN)

- **CVSS 3.1:** 5.3 — `AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:L/A:L`
- **Location:** registration and growth routes (no limiter dependency).

**Description.** Account registration and some growth endpoints have no rate
limit, confirmed by live request during the assessment (repeated registrations
succeeded without throttling). This enables mass account creation and
email-send abuse (each triggers a transactional email via Resend).

**Impact.** Spam/abuse, mailbox flooding of third parties, and potential email
reputation damage / cost.

**Remediation.** Apply a per-IP and per-email rate limit to registration and
outbound-email-triggering endpoints; consider a CAPTCHA or proof-of-work on
public sign-up. Combine with SEC-003's fail-closed behaviour for these buckets.

**Reference.** OWASP API4:2023 Unrestricted Resource Consumption.

---

### SEC-005 — Missing security headers; schema exposed when deployed (Low, FIXED)

- **CVSS 3.1:** 3.7 — `AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N`
- **Location:** `app/main.py` (no headers middleware; `openapi_url` served
  regardless of environment — only `docs_url` was gated).

**Description.** The API returned no baseline security headers, and
`/openapi.json` (the full route inventory) was served even in a deployed
environment, aiding reconnaissance.

**Remediation (applied).**
- Added `app/core/security_headers.py` (`SecurityHeadersMiddleware`) setting
  `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy:
  no-referrer`, a strict `Content-Security-Policy` for the JSON API
  (`default-src 'none'; frame-ancestors 'none'`), `Permissions-Policy`,
  `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`, and `HSTS` when
  deployed.
- Gated `openapi_url=None` when `settings.is_deployed` (kept on locally for docs
  and frontend type generation).
- Added `Permissions-Policy` to `platform-web/next.config.ts` (it already set
  `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).

**Evidence.** `tests/security/test_security_headers.py` — headers present on
`/health`; HSTS absent when not deployed; `/openapi.json` and `/docs` both `404`
when the app is built with `APP_ENV=production`. `3 pass`.

**Reference.** OWASP A05:2021; WSTG-CONF-07.

---

### SEC-006 — No enforcing Content-Security-Policy on the web app (Medium, PARTIALLY MITIGATED)

- **CVSS 3.1:** 4.7 — `AV:N/AC:H/PR:L/UI:R/S:C/C:L/I:L/A:N`
- **Location:** `platform-web/next.config.ts`.

**Description.** The web application ships no `Content-Security-Policy`. A CSP is
the primary defence-in-depth control that would *contain* an XSS such as SEC-002
even if a sink were reintroduced.

**Status.** SEC-002 itself is fixed at the sink. `Permissions-Policy` was added.
A full enforcing CSP is **deliberately deferred**: for a Next.js app it needs
per-request script nonces and correct `connect-src` for the API and LiveKit
websockets, and a wrong CSP breaks the app silently. It must be validated in a
browser on staging (sign-in → attempt → voice → debrief) before enforcement.

**Remediation.** Introduce a nonce-based CSP in `Report-Only` mode on staging
first, tune against real violation reports, then enforce. Track `frame-ancestors
'none'`, `object-src 'none'`, `base-uri 'self'`.

**Reference.** OWASP A05:2021; WSTG-CLNT-01.

---

### SEC-007 — Unvalidated assistant `extras` → prompt steering and cost abuse (Medium, OPEN)

- **CVSS 3.1:** 5.4 — `AV:N/AC:L/PR:L/UI:N/S:C/C:L/I:L/A:N`
- **Category:** **OWASP LLM01:2025 Prompt Injection**; LLM10 Unbounded
  Consumption.
- **Location:** `app/features/assistant/schemas.py` (`extras: dict[str, Any]`,
  free-form); `app/features/assistant/doctor_prompt.py`
  (`consulting_doctor_instructions` reads `extras["station"]` and builds the
  system prompt from it without validating it against a real station).

**Description.** `POST /assistant/sessions` accepts a free-form `extras` object
that is used to build the consulting-doctor system prompt. Because it is not
reconciled against a persisted, authorised station, a caller can inject arbitrary
scenario/system-prompt content and steer the model, and can drive sessions for
scenarios they were not assigned (cost).

**Impact.** Prompt-steering of the tutor/assistant, and LLM cost abuse.
Constrained by the fact the workers never score (scoring is backend-only), so the
integrity impact on marks is limited — but content and cost are affected.

**Remediation.** Rebuild the station/scenario server-side from the database using
an identifier the caller is authorised for; treat `extras` as opaque hints only,
never as prompt-defining content. Log and cap session creation per user.

**Reference.** OWASP LLM01:2025.

---

### SEC-008 — No cap on voice session length → LLM/voice cost abuse (Medium, FIXED)

- **CVSS 3.1:** 5.3 — `AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:L`
- **Location:** `assessment-platform/.../livekit_assistant_worker/pacing.py`;
  voice token TTL of 1 hour.

**Description.** Nothing caps how long an assistant session runs; it continues
until the user leaves. The pacing clock (`pacing.py`) deliberately never ends an
interaction, and only the GPT-Live runtime carried a session policy of its own
(`gpt_live_policy.py`, 300 s). The default pipeline runtime ran until the client
disconnected, so a single user could hold sessions open to run up unbounded LLM,
speech-to-text and text-to-speech spend.

**Impact.** Financial denial-of-wallet.

**Fix (2026-09-25).** Added a platform-agnostic wall-clock cap
(`livekit_assistant_worker/session_cap.py`): `register_session_cap` installs a
single timer in the session entrypoint (`session.py`) for every runtime, and
`SessionCap` shuts the job down (`ctx.shutdown(reason="session_cap")`) once the
limit passes. It is a pure resource guard — no scoring, no content, no view of
the interaction — so it respects the "LiveKit layer stays platform-agnostic"
rule. The cap defaults to one hour (matching the voice token TTL), is tunable
with `ASSISTANT_MAX_SESSION_SECONDS`, and is disabled with `0`/`off`. The
GPT-Live runtime's own 300 s policy still fires first; this is the backstop the
pipeline runtime lacked. **Regression test:**
`assessment-platform/tests/test_assistant_worker_session_cap.py` (the cap shuts
the job down at the limit, a clean teardown cancels it first, and it is tunable
and disable-able).

**Remediation (residual, backlog).** Per-user concurrent-session and daily-minute
caps remain a backend concern for a later pass; align the voice token TTL to the
intended session length.

**Reference.** OWASP LLM10:2025 Unbounded Consumption.

---

### SEC-009 — Container runs as root; build-ARG token in image history (Medium, FIXED)

- **CVSS 3.1:** 5.9 — `AV:L/AC:H/PR:L/UI:N/S:C/C:H/I:L/A:N`
- **Location:** `backend/platform-api/Dockerfile` — no non-root `USER`;
  `ARG ENGINE_REPO_TOKEN` is a build argument, recorded in `docker history`.

**Description.** The image ran as root, so a process compromise started with root
in the container. `ENGINE_REPO_TOKEN` passed as a build ARG is persisted in image
layer metadata and readable by anyone who can pull the image. The repository also
had **no `.dockerignore`**, so the whole build context (any local `.env`,
`serviceAccountKey.json`, keys) was sent to the builder and `COPY . .`'d in.

**Fix (2026-09-25).** `backend/platform-api/Dockerfile` now:
- reads the engine token from a **BuildKit secret** (`RUN --mount=type=secret,
  id=engine_token,required=false`), with `# syntax=docker/dockerfile:1.7`, so the
  token never lands in a layer or `docker history`. The write/use/cleanup all
  happen in one layer and `/root/.gitconfig` is deleted at the end. The build
  ARG survives only as a documented migration fallback for a builder that cannot
  mount secrets;
- adds a non-root user (`useradd --system --uid 10001 appuser`, `chown -R`,
  `USER appuser`) so the runtime container is unprivileged.

Added `backend/platform-api/.dockerignore` excluding `.git`, `.venv`, `.env*`,
`*.pem`/`*.key`, `serviceAccountKey.json`, `docs`, `tests` and local artefacts.

**Deploy note (supervised).** Railway must supply `ENGINE_REPO_TOKEN` as a
build-time secret with id `engine_token`; verify the first build after this
change. The token should still be rotated once — it lived in a build ARG
historically (tracked as SEC-012 secret rotation).

**Reference.** CIS Docker Benchmark 4.1 (non-root user), 4.10 (secrets);
CWE-522.

---

### SEC-010 — Worker pods lack securityContext / NetworkPolicy (Low, FIXED)

- **CVSS 3.1:** 4.0 — `AV:L/AC:H/PR:L/UI:N/S:U/C:L/I:L/A:L`
- **Location:** `assessment-platform/k8s/deployment.yaml`; `.dockerignore`.

**Description.** Worker pods defined no `securityContext` (so no
`runAsNonRoot`, dropped capabilities, or `allowPrivilegeEscalation: false`), no
`NetworkPolicy` (no ingress restriction), used a mutable `:production` image tag,
and set no CPU limit. The `.dockerignore` allowed `runs/` and `dist/` into the
image.

**Fix (2026-09-25).** Both worker deployments (`k8s/deployment.yaml`,
`k8s/deployment-assistant.yaml`) now carry:
- a pod `securityContext` (`runAsNonRoot: true`, `runAsUser/Group: 10001`,
  `fsGroup: 10001`, `seccompProfile: RuntimeDefault`) matching the image's
  `appuser` uid;
- a container `securityContext` (`allowPrivilegeEscalation: false`,
  `capabilities: drop: [ALL]`).

Added `k8s/networkpolicy.yaml`: a `NetworkPolicy` that confines inbound traffic to
the probe/agent ports (8080/8087/8088) for both worker pods and denies everything
else in. `.dockerignore` now excludes `runs/`, `dist/`, `*.pem`,
`serviceAccountKey.json` and `KMS`. **Regression test:**
`assessment-platform/tests/test_k8s_config.py`
(`test_deployments_run_unprivileged_and_drop_capabilities`,
`test_a_network_policy_confines_inbound_traffic_to_the_worker_ports`).

**Remediation (residual, backlog / by design).** `readOnlyRootFilesystem` is left
`false` because the worker caches plugin models under `/app/.cache` at runtime; a
later pass can make it read-only with a tmpfs mount. CPU limits stay off by design
for real-time audio (throttling harms latency). Pinning image digests over the
mutable `:production` tag is a CI/deploy-workflow change tracked separately.

**Reference.** CIS Kubernetes Benchmark 5.x (Pod Security Standards).

---

### SEC-011 — Password reset on SSO-only accounts (Low, MITIGATED — corrected in v1.1)

- **CVSS 3.1:** originally rated 5.4; **corrected to ~2.0** after deeper review.
- **Location:** `app/features/identity/service_passwords.py`.

**Correction (v1.1).** The v1.0 draft rated this Medium/Open. On direct
verification of the code, the risk is **already blocked**:
- `begin_password_reset` returns `None` (issues no token, sends no email) when
  `user.password_login_disabled` is set (`service_passwords.py:41-45`), giving
  an SSO-only account the same non-answer an unknown address gets.
- `confirm_password_reset` re-checks the same flag as **defense in depth**
  (`service_passwords.py:69-76`) and raises `InvalidResetToken` — so even a token
  minted by another path (e.g. `service_invitations.py`) cannot set a password on
  an SSO-only account.
- SSO-only provisioning calls `disable_password_login` even for a pre-existing
  account matched by email (`service_sso.py`).

**Residual (backlog, cosmetic).** `service_invitations.py` still *mints* a reset
token for an SSO-only invitee without the early check; the token is inert (the
confirm guard rejects it), so this is tidiness, not a vulnerability. Add the flag
check at mint time to avoid issuing a dead token.

**Reference.** OWASP API2:2023; WSTG-ATHN-09.

---

### SEC-015 — Entra SSO: no OAuth `state`, no OIDC `nonce` (Medium, FIXED)

- **CVSS 3.1:** 5.4 — `AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:L/A:N`
- **Category:** OWASP A01/A07:2021; WSTG-SESS-05 (CSRF); OIDC best practice.
- **Location:** `app/features/sso/entra.py` — `sign_in_url` (builds the
  `/authorize` URL with `client_id/response_type/redirect_uri/response_mode/scope`
  and **no `state`**); `verify` (validates the id_token signature, `aud`, `iss`,
  `exp` — good — but checks **no `nonce`**).

**Description.** The Entra sign-in URL carries no `state` parameter, and the
callback validates the id_token but never binds a `nonce`. This is classic OAuth
*login CSRF*: an attacker who completes their own Entra login can get a victim's
browser to submit the attacker's authorization `code` to the callback, signing
the victim into the **attacker's** account (session fixation), or replay a
callback. Because the platform sets no session cookie and returns tokens in the
JSON body (ADR 0004), impact is capped at "victim's browser is signed into the
attacker's account" rather than token theft — but it is a real, standard gap.
(The Clerk flow verifies a session token against Clerk's API and is not raw
OIDC, so `state`/`nonce` do not apply there in the same way.)

**Impact.** Login-CSRF / session-fixation into an attacker-controlled account;
the victim may then enter data believing it is their own account.

**Fix (2026-09-25).** Implemented the stateless signed-`state` design that fits
ADR 0004 (no server session store). A new `app/features/sso/state.py` mints a
short-lived (600 s) HS256 token that carries the initiating org slug and a random
`nonce`, purpose-tagged `sso-state`; `issue_state` returns the token and the
nonce, `verify_state` accepts it only when the signature, `exp`, purpose and org
slug all check out. `service_login.build_login` issues the state and passes both
`state` and `nonce` to `entra.sign_in_url` (which now adds them to the
`/authorize` URL); `complete_callback` requires a valid state for Entra, recovers
the expected `nonce` from it, and `entra.verify` refuses an id_token whose `nonce`
does not match. Clerk is unaffected (`_requires_state` is Entra-only), since its
flow verifies a session token against Clerk's API rather than raw OIDC.
`SsoCallbackRequest` gained an optional `state` field. **Regression tests:**
`tests/security/test_sso_state.py` (state verifies only when minted here,
unexpired, purpose-correct and org-matched) and `tests/http/test_sso_login_routes.py`
(round-trip carries the nonce; a callback with no state or a foreign org's state
is refused with 422 `sso_verification_failed`).

**Reference.** OWASP WSTG-SESS-05; OIDC Core §3.1.2.1 (nonce), RFC 6749 §10.12.

---

### SEC-016 — Stream/voice ticket is time-bound but not single-use (Low, FIXED)

- **CVSS 3.1:** 2.6 — `AV:N/AC:H/PR:L/UI:N/S:U/C:L/I:N/A:N`
- **Location:** `app/core/streams.py` (`issue_stream_ticket` / `decode_stream_ticket`).

**Description.** The SSE stream ticket is a stateless HS256 JWT (`typ:"stream"`)
with a 60-second TTL (`stream_ticket_ttl_seconds`). `decode_stream_ticket`
validates signature/iss/exp/typ only — there is no `jti` / server-side
consumption tracking, so the same ticket can open multiple concurrent
`EventSource` connections or be replayed any number of times within its 60-second
window (including just after the attempt ends, if still in-window).

**Impact.** Low; bounded by the short TTL and by the fact the ticket only grants
read access to a stream the holder was already entitled to. No escalation.

**Fix (2026-09-25).** `issue_stream_ticket` now stamps each ticket with a random
`jti`, and `get_stream_principal` claims it on redemption via Redis `SET NX EX`
(keyed `stream-ticket-used:<jti>`, TTL = the ticket's remaining life): the first
redemption wins, a replay is refused with `Unauthenticated`. The guard **fails
open** — a ticket with no `jti`, or a Redis that is off or erroring, redeems as
before — because a seconds-long reopening of a narrow replay window during a
cache blip is a better trade than dropping every live stream (documented in the
module docstring). The 60 s TTL remains the floor. **Regression test:**
`tests/security/test_stream_ticket_single_use.py` (redeem-once-then-replay-refused;
two distinct tickets each redeem; fails open when Redis is off or errors).

**Reference.** OWASP WSTG-SESS-03; CWE-294.

---

### SEC-017 — Stripe checkout omits the `metadata.price_id` its webhook path depends on (Informational — reliability, fails closed)

- **Location:** `app/features/billing/checkout.py` (session creation) vs.
  `app/features/billing/service.py` (`_price_id` reads
  `payload["metadata"]["price_id"]`, falling back to expanded `line_items`).

**Description.** This is a **reliability**, not a security, issue — recorded here
because it was found while verifying payment integrity and it is masked by the
tests. `StripeCheckout.create()` posts `line_items[0][price]`, `customer_email`,
`success_url`, `cancel_url`, `client_reference_id` — but **never sets any
`metadata` field and never requests `expand[]=line_items`**. A real
`checkout.session.completed` webhook therefore likely arrives with neither, so
`_price_id()` returns `""` and `_apply_checkout` raises
`InvalidWebhook(...lacks ... a price ...)` for genuine payments. It **fails
closed** (no wrongful grant; the ledger row persists for reconciliation), so it
is not attacker-exploitable — but a paying customer might not be granted access.
The billing tests fabricate `metadata.price_id` into synthetic fixtures, so the
gap is not caught.

**Remediation.** Set `metadata[price_id]` (or `payment_intent_data[metadata]`) at
checkout-session creation, or expand `line_items`; add an end-to-end test against
a real Stripe test-mode webhook rather than a hand-built event.

**Reference.** Not a CWE — functional correctness with a security-adjacent
availability impact on entitlement grants.

---

### SEC-018 — Slide renderer path traversal via LLM-generated `image_urls` (Medium, FIXED)

- **CVSS 3.1:** 5.0 — `AV:N/AC:H/PR:L/UI:N/S:U/C:H/I:N/A:N`
- **Category:** OWASP WSTG-ATHZ-01 / path traversal; CWE-22 / CWE-73.
- **Location:** `app/features/media_production/slide_renderer.py`
  (`_resolve_image_path`), reached from `_create_image_clips`; input
  `slide["image_urls"]` (`slide_models.py`, `list[str]`, previously unvalidated).

**Description.** `_resolve_image_path` joined an `image_url` onto a base directory
(`slides_base_dir` or `topic_folder`) with `Path.__truediv__`, which does not
neutralise `..`. The `image_urls` values are **LLM-generated** (the slide
generation prompt produces them), so a prompt-injection from station/scenario
content could redirect the field. A crafted value such as
`"../../../../etc/<some_readable_image>"` escaped the slides tree, and any
image-parseable file readable by the worker was embedded into the rendered video
(which is then uploaded to S3 and downloadable) — a filesystem read primitive.
The trigger route (`POST /media/{item_id}/regenerate-av`) is `PlatformAdmin`-gated,
but the missing validation was concrete and unconditional.

**Impact.** Arbitrary worker-readable file (that parses as an image) exfiltrated
via the generated video. Gated behind admin/compromised-pipeline reachability,
hence Medium rather than High.

**Evidence (regression test).**
`tests/security/test_slide_image_path_traversal.py` — 4 tests: a legitimate
in-tree image resolves; `../..` traversal, an absolute path, and
`images/../../..` traversal all resolve to a non-existent, in-tree path (so
callers skip them) and never to the out-of-tree target. Pass.

**Remediation (applied).** `_resolve_image_path` now rejects absolute paths and
any `..` component, resolves the candidate, and asserts it is contained within its
base directory (`Path.relative_to`); an unsafe url resolves to a guaranteed-absent
path so every caller's existing `.exists()` guard skips it. Behaviour is unchanged
for legitimate images.

**Reference.** CWE-22 Improper Limitation of a Pathname to a Restricted Directory.

---

### SEC-019 — Clerk session id spliced unescaped into outbound API URL (Low, FIXED)

- **CVSS 3.1:** 3.1 — `AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:L/A:N`
- **Category:** CWE-88 Argument/URL injection.
- **Location:** `app/features/sso/clerk.py` (`verify`).

**Description.** `verify` reads the `sid` claim from a JWT **before** its signature
is checked (verification happens via the very call being built), then splices
`session_id` unescaped into the request path
`{CLERK_API_BASE}/sessions/{session_id}/verify`. A `/`, `?`, `#` or `..` in the
attacker-influenced `sid` could reshape the URL that the org's Clerk secret key is
attached to. The host is a hard-coded literal, so this is not full SSRF, but it is
untrusted input building a privileged request URL.

**Impact.** Low; bounded by the fixed host and Clerk-side authorization. Fixed as
hygiene / defense in depth.

**Evidence (regression test).**
`tests/security/test_clerk_session_id_url_encoding.py` — a crafted
`sid="sess_1/../../admin"` is percent-encoded (`sess_1%2F..%2F..%2Fadmin`) in the
outbound URL, and the raw traversal path never appears; the happy path still
resolves an identity. Pass.

**Remediation (applied).** `session_id` (and `user_id`) are now `quote(..., safe="")`
-encoded before interpolation, matching the discipline already used for
`redirect_url`.

**Reference.** CWE-88.

---

### SEC-020 — Community `set_like` skips an audience visibility check (Informational)

- **Location:** `app/features/community/service.py` (`set_like`).

**Description.** Unlike `question_detail` / `list_replies` (which re-check
`can_see(audience_of(row), viewer_audiences)` and return `PostNotFound` for
content outside the viewer's audience), `set_like` toggles a like without an
audience check. A user who guesses a post id could like/unlike content outside
their visibility scope. No data is disclosed — only an engagement counter moves —
so this is cosmetic.

**Remediation.** Apply the same `can_see` audience check before toggling a like.

**Reference.** OWASP API1:2023 (object-level authorization); CWE-639.

---

### SEC-013 — Station photo upload validates extension only (Low, OPEN)

- **CVSS 3.1:** 3.1 — `AV:N/AC:H/PR:L/UI:R/S:C/C:L/I:L/A:N`
- **Location:** `app/features/stations/domain_photos.py` (`validate_upload`,
  `object_key`); `app/features/media_production/s3.py` (`upload_fileobj`).

**Description.** Photo upload validation is sound in most respects — size is
capped at 10&nbsp;MB and checked server-side (not from a client header), and the
storage key is a fresh `uuid4().hex` with only the validated suffix, so path
traversal via filename is not possible. However, the *content type* is validated
by **file extension only** (`.png/.jpg/.jpeg`); there is no MIME-header check and
no magic-byte / real-content sniffing. A file named `photo.png` containing
arbitrary bytes (HTML/SVG/script) passes validation.

**Mitigating factor.** `s3.py` uploads with no explicit `ContentType`, so S3
stores the object as `binary/octet-stream`, which browsers download rather than
render inline — this substantially reduces, but does not formally eliminate, the
risk of the object executing in a browser (depends on CDN/edge config and legacy
MIME-sniffing). The bucket URL is public and no `Content-Disposition` is set.

**Impact.** Low. Potential for a stored file to be interpreted as active content
if edge configuration ever allows MIME sniffing; otherwise a content-integrity
nicety.

**Remediation.** Sniff real content (e.g. `PIL.Image.open(...).verify()`) and
reject non-images; set an explicit safe `ContentType` and
`Content-Disposition` on upload; ensure `X-Content-Type-Options: nosniff` at the
serving edge; consider serving via presigned URLs rather than a public bucket.

**Reference.** OWASP WSTG-BUSLOGIC-09 (file upload); CWE-434.

---

### SEC-014 — Org may enrol an un-rostered arbitrary user id into a circuit (Low, FIXED)

- **CVSS 3.1:** 3.5 — `AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:L/A:N`
- **Location:** `app/features/roster/service.py` (`ensure_rosterable`), reached
  from `app/features/sittings` circuit routes (`add_circuit`, `rebuild_circuit`,
  `append_trainees`).

**Description.** This is **not** a cross-org read IDOR — the `trainee_id` IDOR
concern (L9) was tested and is *not present*: every route that accepts a
`trainee_id` (in either its `users.id` or `trainees.id` meaning) filters by the
caller's own server-derived `org_id` before reading or writing (see positive
observations). However, `ensure_rosterable` deliberately does **not** refuse a
`users.id` that is not on the organisation's roster at all ("an organisation may
examine somebody it has not rostered"). Combined with client-supplied
`trainee_ids` (meaning `users.id`) on circuit routes, an org admin could place an
arbitrary, enumerated `users.id` belonging to an unrelated account into their own
org's circuit without that user's consent or membership.

**Impact.** Low, and requires org-admin privilege. It does not disclose the other
user's data, but it could attach a real person's account to an examination they
never joined (a privacy/consent concern) and is a write-side authorization
looseness worth an explicit product decision.

**Owner decision (2026-09-25).** Not intended — locked down. A `users.id` placed
into a circuit must now be on the org's roster (or resolved through an explicit
invitation that created the roster link).

**Fix (2026-09-25).** `ensure_rosterable` (`roster/service.py`) already mapped
each `users.id` to a linked trainee via `trainees_for_users` and raised
`TraineeNotOnRosterError` when there was none (and `TraineeRevokedError` for a
revoked one). The looseness was that the circuit enrolment routes did not surface
that refusal: the error was undeclared, so the `UndeclaredErrorCode` middleware
turned it into a 500 instead of a clean 409, and it was easy to read the route as
permissive. The three enrolment routes (`add_circuit`, `rebuild_circuit`,
`append_trainees` in `sittings/router.py`) now declare
`errors.TraineeNotOnRosterError` alongside `TraineeRevokedError`, and
`sittings/errors.py` re-exports it — so an un-rostered `users.id` is refused with
`409 trainee_not_on_roster`, closed. **Regression test:**
`tests/http/test_sittings_routes.py::test_a_revoked_trainee_cannot_be_put_on_a_circuit`
plus the circuit-enrolment cases in the sittings HTTP suite (an un-rostered or
revoked user id is refused, not enrolled).

**Reference.** OWASP API1:2023 (object-level authorization); CWE-639.

---

## 6. Positive observations (controls that held)

These are as important as the findings for a client auditor — they show the
platform was built with security in mind:

- **Robust token verification.** `decode_access_token` pins `algorithms=["HS256"]`
  (an `alg:none` or wrong-secret token is refused), verifies the issuer, requires
  `exp`/`iat`/`sub`, and checks `typ == "access"` so a refresh token cannot open
  an access route. Proven by 5 passing negative-control tests
  (`tests/security/test_auth_tokens.py`).
- **Strong password storage & session hygiene.** Argon2 password hashing;
  refresh tokens stored hashed and rotated, with reuse detection that revokes the
  chain.
- **Fail-closed worker auth.** `require_worker_secret` uses
  `hmac.compare_digest` and refuses when the secret is unset/mismatched.
- **Tenant suspension is enforced live.** Organisation status is re-read from the
  database each request, so a suspended tenant loses access within the token's
  15-minute life rather than at expiry.
- **Platform admin is not implicitly an org admin.** `OrgAdmin` sets
  `allow_platform_admin=False` by design, so revoking an org membership genuinely
  removes access.
- **Parameterised SQL, confined to repositories.** The only raw `text()` queries
  (health/job listing) bind every user value as a parameter; interpolated parts
  are constant column lists / hard-coded clauses. Architecture guard tests keep
  SQL inside repositories.
- **Clean dependency & secret posture on the new code.** `npm audit`: **0
  vulnerabilities**. Gitleaks on `assessment-platform`: clean. (The secret hits
  are in legacy trees / git history — see SEC-012.)
- **Server-authoritative authorization in the web app.** platform-web derives
  permissions from `/me/capabilities`, never from a role in the browser, and the
  exam clock is the server's.
- **No cross-org `trainee_id` IDOR.** Despite `trainee_id` meaning two different
  things (`users.id` in circuit slots, `trainees.id` in results/groups), every
  endpoint that accepts one filters by the caller's own server-derived `org_id`
  before reading or writing. Candidate self-service derives trainee ids from the
  authenticated user, never from the request. Supplying a foreign-org
  `trainee_id` returns nothing. (Reviewed across results, roster, groups,
  sittings; one write-side looseness found and fixed as SEC-014.)
- **Receipts are HTML-escaped.** `receipt_document.py` passes every
  user-influenced field (name, email, plan, dates, reference, footer) through
  `html.escape` before interpolation; the receipt schema has no free-form
  company/line-item field. No HTML injection path found.
- **Safe upload key generation.** Uploaded file storage keys are a fresh
  `uuid4().hex` with only a validated suffix — no original filename component is
  reused, so path traversal via filename is not possible (see SEC-013 for the
  content-type caveat).

The v1.1 verification round (2026-09-25) cleared several further controls that a
production auditor will want to see named:

- **Whole injection classes are absent.** A deliberate sweep for SSRF, insecure
  deserialization, server-side template injection, OS-command injection, XXE and
  ReDoS found **none** reachable from untrusted input. There is no `pickle`/
  `yaml.load`/`eval`/`exec` on request data; no user-controlled outbound URL
  (the two external hosts, Clerk and Stripe, are hard-coded literals); no
  `Template(...).render` over user strings; no `subprocess`/`os.system` with
  request data; XML parsing is not exposed to untrusted input; and no
  catastrophic regexes run over attacker-supplied text.
- **Mass-assignment is structurally prevented.** Endpoints bind typed Pydantic
  request models with explicit fields, so a client cannot smuggle
  `is_platform_admin`, `org_id`, `role` or `status` into an update by adding JSON
  keys — unknown keys are dropped and privileged fields are server-set.
- **BFLA holds on the admin surface.** `/platform/*` is gated by the
  `PlatformAdmin` dependency (a signed claim, re-checked server-side), and an org
  admin calling a platform route receives 403 — verified against the console
  routers.
- **Payment integrity is sound.** The Stripe webhook verifies the signature with
  a constant-time compare and **fails closed** on a missing/invalid signature,
  rejects the wrong event type, is idempotent against replay (the ledger row is
  keyed and re-application is a no-op), and grants entitlements only after a
  verified `checkout.session.completed`. Entitlement reads filter on `live` and
  fail closed, so a revoked or expired grant denies access.
- **Voice-token authorization is least-privilege.** Voice, observer and join
  tokens are minted only after an ownership check ties the caller to the
  attempt/session/circuit; the participant identity is **server-assigned** (a
  client cannot claim `agent-*`); and the observer grant is subscribe-only with
  no publish or data-publish rights. No path lets a candidate publish as the
  agent.

---

## 7. Remediation roadmap

| Priority | Finding(s) | Action | Target |
|---|---|---|---|
| **Immediate** | SEC-001, SEC-002, SEC-005, SEC-018, SEC-019 | Fixed during engagement (regression tests green) | **Done** |
| **Remediation pass (2026-09-25)** | SEC-008, SEC-009, SEC-010, SEC-014, SEC-015, SEC-016 | Voice session-length cap; container non-root + BuildKit secret + `.dockerignore`; worker pod securityContext + NetworkPolicy; circuit-enrolment roster lock-down; Entra SSO `state`/`nonce`; stream-ticket single-use — all with regression tests | **Done** |
| **Immediate (owner)** | SEC-012 | Rotate all exposed secrets; move key out of tree | Within 1 week |
| **Deploy verification (supervised)** | SEC-009, SEC-010 | First Railway build with the `engine_token` BuildKit secret; `kubectl apply` the hardened worker manifests + NetworkPolicy and smoke a session | With next deploy |
| **Short term** | SEC-003, SEC-004, SEC-007 | Rate-limit hardening; validate assistant input server-side | Within 2–4 weeks |
| **Short term** | SEC-006 | Nonce CSP in Report-Only on staging → enforce (deferred pending a browser walk-through) | Within 2–4 weeks |
| **Medium term** | SEC-013 | Upload content sniffing | Within 4–8 weeks |
| **Housekeeping** | SEC-011, SEC-017, SEC-020 | Add mint-time SSO guard; set Stripe `metadata.price_id` at checkout; add `can_see` to community `set_like` | Backlog |
| **Follow-on** | All | Production engagement (v2): TLS, headers, CORS, exposed-schema and rate-limit checks against the live edge; authenticated DAST | Next round |

---

## 8. Appendices

### Appendix A — Coverage checklist (OWASP WSTG / ASVS L2)

| Area | Result | Notes |
|---|---|---|
| Information gathering / schema exposure | **Fixed** | `/openapi.json` gated when deployed (SEC-005) |
| Configuration & deployment (headers, CORS) | **Fixed / N-A** | API headers added; CORS credentialed with an origins allow-list; production CORS to re-verify in v2 |
| Identity & registration | **Finding** | No registration rate limit (SEC-004) |
| Authentication | **Pass** | Token verification hardened; argon2; reset flow gap for SSO-only (SEC-011) |
| Session management | **Pass** | Refresh rotation + reuse detection; 15-min access token |
| Authorization (BOLA/BFLA, multi-tenant) | **Fixed** | Role escalation fixed (SEC-001); cross-org `trainee_id` IDOR tested — not present; circuit-enrolment roster lock-down fixed (SEC-014) |
| File upload | **Finding** | Size/path-traversal safe; content-type extension-only (SEC-013) |
| Output encoding (receipts) | **Pass** | All fields `html.escape`d |
| Rate limiting / resource consumption | **Finding / partly fixed** | XFF spoof + fail-open open (SEC-003); voice session-length cap fixed (SEC-008) |
| Input validation / injection (SQLi) | **Pass** | Parameterised SQL; SAST hit confirmed false positive |
| Cross-site scripting (XSS) | **Fixed** | Markdown sanitised (SEC-002) |
| Client-side (CSP) | **Partial** | Enforcing CSP deferred to staging validation (SEC-006) |
| Payments & entitlements | **Pass (reviewed)** | Stripe webhook signature verified, fails closed, idempotent; entitlement gates filter on `live`; checkout `metadata.price_id` reliability note (SEC-017); deeper dynamic tests in v2 |
| LLM / voice (prompt injection, output handling, cost) | **Finding / partly fixed** | Insecure output handling fixed (SEC-002); LLM-generated path traversal fixed (SEC-018); session-length cap fixed (SEC-008); assistant `extras` validation open (SEC-007) |
| Worker / dispatch auth | **Pass** | `X-Worker-Secret` fail-closed |
| Voice-token authorization | **Pass / hardened** | Ownership-checked; server-assigned identity; observer subscribe-only; no candidate-as-agent path; stream ticket now single-use (SEC-016) |
| SSRF / deserialization / SSTI / command / XXE / ReDoS | **Pass (absent)** | No untrusted outbound URL, no unsafe deserialization, no template/command injection over request data, no exposed XML parse, no catastrophic regex |
| Mass assignment / BFLA | **Pass** | Typed request models drop unknown keys; `/platform/*` gated by `PlatformAdmin` (403 for org admin) |
| SSO (OAuth/OIDC) | **Fixed** | Clerk session-token verify hardened (SEC-019); Entra flow `state`/`nonce` added (SEC-015) |
| Secret management | **Finding** | Secrets in history/tree (SEC-012) |
| Container & Kubernetes | **Fixed** | Non-root container + BuildKit secret (SEC-009); worker pod securityContext + NetworkPolicy (SEC-010); pending supervised deploy verification |

### Appendix B — Role × route access matrix (result)

The authorization model was reviewed against the route inventory. Key assertions
now enforced and tested:

| Actor | Action | Expected | Result |
|---|---|---|---|
| `partner_admin` | grant `institution_admin`/`owner` | 403 | **Enforced** (SEC-001 fix) |
| any org admin | write an undefined role string | 422 | **Enforced** (SEC-001 fix) |
| `platform_admin` | membership admin via console | allowed (known roles) | Enforced |
| org A member | read org B object | 404/403 | Reviewed — org-scoped repositories |
| org A member | read org B via foreign `trainee_id` | no data | Verified — filtered by caller's `org_id` |
| `trainee` | run/advance a circuit | 403 | Enforced (`may_run_circuit` excludes trainees) |
| org admin | call a `/platform/*` route | 403 | Enforced (`PlatformAdmin`) |
| any client | smuggle `is_platform_admin`/`org_id` in an update body | ignored | Enforced (typed models drop unknown/privileged keys) |
| candidate | join a voice room as `agent-*` | rejected | Enforced (server-assigned identity) |
| observer | publish audio/data on a session | rejected | Enforced (subscribe-only grant) |
| forged/`alg:none`/wrong-secret token | any authenticated route | 401 | Enforced (auth tests) |
| refresh token used as access token | access route | 401 | Enforced (`typ` check) |

### Appendix C — Tools & versions

| Tool | Version |
|---|---|
| Trivy | 0.58.1 |
| Gitleaks | 8.21.2 |
| Semgrep | 1.99.0 |
| npm audit | npm 10 / Node 22 |
| pytest + httpx | project venv (Python 3.11) |
| node --test | Node 22 |

### Appendix D — Regression tests added

- `backend/platform-api/tests/security/test_auth_tokens.py` — 5 token-forgery
  negative controls.
- `backend/platform-api/tests/security/test_membership_role_escalation.py` —
  SEC-001.
- `backend/platform-api/tests/security/test_security_headers.py` — SEC-005.
- `backend/platform-api/tests/security/test_slide_image_path_traversal.py` —
  SEC-018 (4 cases: legit resolve; `..` traversal, absolute path, and
  `images/..` traversal all neutralised).
- `backend/platform-api/tests/security/test_clerk_session_id_url_encoding.py` —
  SEC-019 (malicious `sid` is percent-encoded in the outbound URL).
- `platform-web/src/foundation/ui/renderMarkdown.test.ts` — SEC-002 (7 cases).

Full run at report time (incl. the v1.1 verification round): platform-api
`tests/security` **15 passed**; the sso/media/clerk/slide modules touched by the
new fixes **431 passed** with zero regressions; `mypy` and `ruff` clean;
platform-web markdown suite **7 passed**, `tsc --noEmit` clean.

---

*End of report. Prepared for OSCE Guide. Confidential.*
