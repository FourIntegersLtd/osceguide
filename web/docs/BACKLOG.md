# Backlog

The one list of pending work for the live stack (platform-web, platform-api,
assessment-platform): what it still does not do, and the few things it does
differently on purpose. It replaces `port-gaps.md`, `parity-fix-plan.md`,
`gap-closure-plan.md`, `ai-practice-b2c-parity-checklist.md` and platform-api's
`docs/OPEN-QUESTIONS.md` (removed 2026-09-25, recoverable from git history).
Rows with an ID keep it, so the code comments that cite one still resolve.
Don't start another list in another repo. Add a row here.

**Rules for this file**

- Only open work. When an item lands, delete its row in the same commit.
- Re-check a row in the code before scheduling it. The files this replaces
  drifted both ways: rows marked open that were built, and the reverse.
- `npm run ci` runs `scripts/audit-ledger-routes.mjs` over this file. A route
  named here as fact must exist in `openapi.json`; a route that does not exist
  must be written as missing ("there is no …").

Checked against the code on 2026-09-25.

## Open: engineering

### Institution (assess)

| Item | State |
|---|---|
| Resend a staff invitation | There is no resend route for a staff membership. Trainees have one (`POST /orgs/{org_slug}/trainees/{trainee_id}/resend-invitation`) |
| A candidate reading their published review | No candidate-facing read of a circuit's supervisor review or their slot review. The largest thing the sittings port could not carry |
| Cohort export (the markdown readout) | Not built. Low priority |

### Authoring

`capabilities/authoring/api/scope.ts` names the backend's asymmetries:

- Platform scope has no brief edit and no draft-version delete (see decision D4 below).
- There is no delete for an exam or a template.

### Consumer (train)

| Item | State |
|---|---|
| Delete your own account | There is no delete route for `/me`. Needs a data-handling decision too |
| Upload your own profile photo | `PhotoUpload` has a real caller for station photos (`stations/router_photos.py`); nothing supplies an `upload` for a person's avatar. Reuse the station-photo route family |
| Voice onboarding scenes | No onboarding-scenes route in `assistant/`; needs design as well as code |
| Assistant cards | `parseAssistantCardPayload` (`foundation/livekit/guidance/contracts.ts`) has no receiver |

### Peer practice

The screens match legacy and drive the accept/decline handshake (proof:
`.claude/skills/verify/features/marketplace.md`). Still open:

| # | Item | State |
|---|---|---|

### Backend and workers

| # | Item | State |
|---|---|---|
| B-2 | `plans.exam_code` is nullable | `_apply_checkout` refuses a plan with no `exam_code`, but only *after* the card is charged, and no test pins that refusal. Fix: a NOT NULL migration and one test |
| B-4 | Receipts for old payments | Payments taken before the receipt columns existed have no `receipt_id`, so `/me/receipts` does not list them. Either mint the ids retrospectively or leave those payments to support |
| A-1 | The assistant worker hardcodes its backend paths | `livekit_assistant_worker/metadata.py` spells out `/api/worker/assistant-sessions/...` and `/api/worker/sessions/{id}/complete` instead of reading `VOICE_BACKENDS_JSON` as the assessment worker does. platform-api mounts them at exactly those paths. A small, backwards-compatible worker change fixes it |
| P-2 | `never_doctor` must be set at migration | b2c's matcher hardcoded three people who must never be assigned the doctor role. platform-api has a `never_doctor` column on `practice_history`, but no migration step sets it. Without that flag, those three will be assigned as doctor |
| M-1 | Consumer identity import needs a production export | The loader and verify step are written and proven against a real database (dry run, real run, idempotent re-run, tamper-detecting verify). The production export is still needed to size the run and find real-data shapes. Station sets, sittings and org data are not transformed yet |
| G-1 | Partner reconciliation | b2c reconciles partner numbers against Mixpanel and raises spend alerts (`partner_attribution/`, fourteen services). Arrivals, acquisitions, reporters and the funnel are built; reconciliation is not ported. Mixpanel belongs behind a port |
| T-1 | Chunker never size-caps a mid-document section | Only the tail after the last heading is size-capped, so the oracle fixture emits 3815 characters against an 1800 limit. This is legacy behaviour, pinned byte-for-byte by `tests/unit/test_tutor_memory_chunking.py`. Fix it as its own change, updating the oracle in the same commit, then re-index |
| T-3 | Nothing re-indexes tutor material on publish | Material is re-indexed nightly, or by an admin through `POST /api/v1/admin/tutor-memory/reindex`, so a correction made in the morning is not searchable until the next night. Fix: let the job take one source, then call it from `media.service.publish` |
| V-1 | The debrief clock and walk-through prompt are unproven live | Engine `engine-v0.8.0` (assessment-platform `fd5180b`) and platform-api `835d34e` are on staging. Run one staging debrief (`verify-voice-station`): the tutor walks the plan, never mentions time, and closes near 10 min. Then Promote the worker and platform-api together |
| V-2 | The debrief rarely reaches the differential | Missed in 14 of 16 bench debriefs even with the clock (`scripts/debrief_bench.py`, `runs/debrief-shipped-clock.json`). Needs a prompt change measured on the bench, not a new rule on its own |

### Website hosting

| # | Item | State |
|---|---|---|
| W-1 | Enforcing the CSP blocks every script | Found on staging 2026-09-26 with `PLATFORM_WEB_CSP_ENFORCE=true`: pages are prerendered, so their `<script>` tags carry no nonce, and the enforced policy (`'nonce-…' 'strict-dynamic'`, where `'self'` no longer counts) blocks them all. The page never hydrates and loads forever. Staging and production stay on Report-Only until pages render per request (the nonce needs that) or the policy stops relying on a nonce. Prove it on staging before setting the variable again |
| W-2 | The analytics consent prompt shows where no analytics can load | Staging and previews resolve no GA id (`foundation/analytics/gaMeasurementId.ts`), yet the "Allow analytics" prompt still covers the page. Skip it when there is no id |

## Open: enterprise readiness

What an institution's procurement and IT security review will ask for and we
cannot yet show. Checked against the code on 2026-09-26. Everything here is
about platform-api, platform-web and assessment-platform: until the legacy
backends are switched off, what a buyer uses today is b2c-api and b2b-api.
**Owner** rows need the business owner (accounts, contracts, money); **Eng**
rows are code or docs. Work down the tiers in order.

Already strong, so say so: server-side tenant isolation on every request,
session revocation with refresh-token reuse detection, Argon2 passwords,
fail-closed sign-in rate limits, an append-only `audit_log`, result decisions
kept as revisions with who signed off and released them, rubric prompts stored
per version, Microsoft Entra SSO, and a gated staging-to-production promotion.

### Tier 1: before answering any security questionnaire

| # | Who | Item | State |
|---|---|---|---|
| E-1 | Owner | SEC-012: rotate exposed credentials | The only **Open** High in `platform-api/docs/security/SECURITY-ASSESSMENT-2026-09.md`. Four TLS/LiveKit keys (`misc/*.pem`) and a GCP `serviceAccountKey.json` still sit in the workspace, plus a GitHub credential in history and a GitHub token written into platform-web's local `osceguide-frontend` remote URL (`git remote -v`). Revoke each at its provider, move them to a secrets store, purge history, turn on secret scanning. Done when old credentials are refused |
| E-2 | Eng | The security report reads worse than the code | SEC-002 (platform-web `87485681`), SEC-008 (assessment-platform `a4f82ef`) and SEC-010 (`securityContext` in `k8s/base/deployment.yaml`) are still "pending merge" in the report but have landed. Confirm each is deployed to production, then issue v2.1 so the buyer copy shows 18 of 20 resolved. SEC-006 stays partial until W-1 |
| E-3 | Eng | Erasure and data download are on staging only | Built 2026-09-27 (platform-api `c004c8e`, platform-web `654dfb50`): a daily job erases accounts closed over 30 days (peer recordings once both people are erased), `GET /me/export`, the "Download my data" button, and a corrected privacy policy. Still to do: click the button on staging, confirm the job runs there, then Promote (it carries the `users.closed_at`/`erased_at` migration). The privacy policy now describes this, so production is behind its own policy until then |

### Tier 2: before the first institutional contract

| # | Who | Item | State |
|---|---|---|---|
| E-6 | Owner | Data processing agreement | No DPA template exists. Institutions are the controller for their candidates; we are the processor. Needs a lawyer-reviewed template |
| E-7 | Eng + Owner | Subprocessor list with regions | None published. From code and env: OpenAI (marking, generation), Deepgram (speech to text), Cartesia (text to speech), LiveKit Cloud (voice), Stripe, Resend, Clerk and Microsoft Entra (SSO), AWS S3 (`eu-west-2`, the only region pinned), Railway (Postgres, Redis), Vercel (web), Sentry. Confirm and document the region of each, and name the transfer mechanism for the US ones; the policy says "protected by" without naming it |
| E-8 | Eng | Customer DPIA pack | Institutions must run a DPIA before using us. Write one they can adapt: data flows, AI marking, the human review and sign-off step, retention, subprocessors |
| E-9 | Owner | Cyber Essentials Plus | The baseline UK public-sector buyers check. Weeks, not months. Needs E-1 first |
| E-10 | Owner | NHS Data Security and Protection Toolkit | Required before handling data for NHS organisations (deaneries, trusts). Annual self-assessment |
| E-12 | Eng | Backup restore is untested | Railway PITR is on (chosen 2026-09-26), but no doc says how to restore, and a restore has never been run. Restore production into a scratch database once, time it, write the runbook, state RPO and RTO |
| E-13 | Eng | Uptime monitoring and a status page | Sentry now runs in all three (platform-web through `@sentry/nextjs`, off until `NEXT_PUBLIC_SENTRY_DSN` is set per deployment). No external check on `/health`, no alert rules, no status page |
| E-14 | Eng | A supported concurrency number | Each worker runs 3 replicas with no autoscaling. The last load test (legacy stack, 2026-09-14) passed 27 of 30. Load-test the live stack and publish how many candidates a sitting supports |
| E-15 | Eng | Accessibility | `jsx-a11y`'s recommended rules now fail CI and the statement is published (`/compliances/accessibility`). Still open: axe checks in a browser, a manual WCAG 2.2 AA audit (keyboard and screen reader through every journey), captions for slide videos and transcripts for podcast episodes, and a reply-time commitment for accessibility requests (owner). Update the statement when each lands |
| E-16 | Eng | Results export | No endpoint returns CSV (no `text/csv` anywhere in platform-api). Admins need a sitting's results as CSV, and a candidate's result as PDF. Different from the cohort markdown readout above |
| E-17 | Owner | SLA and support terms | No uptime target, support hours or incident-notification promise is written down. Contracts will ask |
| E-18 | Eng | Stale SSO note | `platform-api/docs/DATA-MODEL.md:141` says "Nothing verifies an identity yet"; `sso/entra.py` and `sso/clerk.py` now verify id tokens server-side. Fix the doc |

### Tier 3: when a deal asks

| # | Who | Item | State |
|---|---|---|---|
| E-19 | Owner | Accredited external pen test | The current report is white-box, local-only, not CREST-accredited, and did not test production. Larger buyers will ask for an accredited test of the deployed service |
| E-20 | Eng | SAML, Google Workspace, NHS CIS2 sign-in | SSO is OIDC through Entra or Clerk only |
| E-21 | Eng | SCIM provisioning | No SCIM. Roster CSV import (`domains/assess/roster/csv.ts`) and bulk trainee add cover small orgs |
| E-22 | Eng | Invoices and purchase orders | `billing/service_settlement.py` settles non-card payments, but nothing issues an invoice or records a PO number |
| E-23 | Eng | API-wide rate limiting | Limits cover sign-in, password reset, register, SSO callback, CV upload and the public site only, and are off without Redis. Add a per-user default and an edge WAF rule |
| E-24 | Eng | Tamper-evident audit | `audit_log` is append-only by convention (no `updated_at`), not enforced. Revoke UPDATE and DELETE on it from the app's database role |
| E-25 | Owner | ISO 27001 or SOC 2 | Only when a contract requires one. Months of work and ongoing cost |
| E-26 | Eng | Metrics | No Prometheus or OpenTelemetry. Sentry and logs are enough until an SLA needs measuring |

## Open: needs a product decision

| # | Question | Recommendation on record |
|---|---|---|
| D2 | Trainee results are narrowed as disclosure policy (`MyResult.tsx`). Show score against threshold once released? | Keep the narrowing; add score vs threshold where the outcome is released |
| D4 | Platform-scope authoring has no brief edit, draft delete or programmes | Keep unless staff actually author briefs |
| D7 | Adding a candidate to a live **exam** circuit is refused (`not_permitted_in_mode`), as legacy did | Confirm. A second candidate means one room, one clock and one transcript marked as one doctor's |
| D8 | Deleting a practice set that has been sat is refused (`set_has_attempts`); legacy orphaned the recordings | Keep. Self-service deletion would be its own audited action |
| D9 | Deleting a non-empty group or in-use cohort is refused | Keep. Residual hole: a cohort that only scheduled sittings is deletable and detaches them |
| D10 | A re-sent invitation spends the previous unused link | Confirm supersede; keeping the old link live is a one-line change |
| — | Live marking: a rubric a supervisor fills **during** a consultation, independent of machine scoring (`LiveMarkingSidebar` marks finished stations only) | Out of scope until wanted; it is a redesign against `marking_layout` |
| — | Preferences: AI-training consent, colleague-waiting email, onboarding replay | Decide which are worth storing |
| — | Push notifications. `web-push` is not a dependency, and legacy's service worker never sent one | Decide whether wanted at all |
| — | Consumer performance extras: RAG by domain, category volume, SCA trends | No data source exists for them; decide what to record first. `exam_date`/`exam_time` are now stored (A4) and read on `UserRead` |
| — | Peer practice: production promotion and two follow-ups | Proven on staging 2026-09-27 (session bc0e13de): match, preparation with a real station, consultation, recording, transcription (5 turns), marking and the doctor's "AI feedback is ready" page. Two fixes found on the way, platform-api 431bfa3 (recording creates the room first) and b6538bf (marking accepts doctor/patient turns), are on staging only: production needs the Promote workflow. Marking in that run needed a support rescore after b6538bf deployed, so the next staging session should confirm it marks unaided. Open: the matcher pairs people when an exam has no published stations (should refuse); the partner's video tile was black 20 s into the consultation (may be the fake camera) |
| — | Ortho CV upload | No decision on record |
| C-1 | **CASC existing databases still mark with the RCGP GP prompt.** A CASC prompt now exists (`platform-api/seeds/prompts/casc_system.txt`, 2026-09-26; b2c never had one, it fell back to SCA) and the seed uses it, but `seed_platform.py` never touches an exam that already exists | Publish a new CASC rubric version carrying the new prompt on staging and production (a deployed write: owner's go-ahead). Existing CASC feedback stays as it was marked |
| B-3 | Referral discounts are built (checkout swaps to the `<plan>_referral` row, the webhook credits £2.50 / £5), but no environment has the 10%-off Stripe prices or `_referral` plan rows yet | Create them per exam after the code deploys; before that, a code at checkout is refused `referral_discount_unavailable` |
| R-2 | Sign-off requires an outcome and a rationale; the proposal also wanted full "readiness" for a pass or fail, and no readiness concept exists | Decide whether readiness is a real gate or drop it from the invariant |
| T-2 | A templated station contributes nothing to the tutor's material index: its blocks are all patient-private or expected answers | Needs a template block role that means "reading material" before any code |
| M-2 | Generation uses b2c's prompts but `gpt-4o-mini` / `gpt-4o`, not b2c's o3/Claude Instructor stack. Podcast audio and slide video rendering are not ported | Decide whether model parity and the AV pipeline are wanted |

## Not gaps: do not re-report

Each is deliberate and explained in the code where it lives.

- **Tenant and account hard delete.** Suspend is the mechanism; a tenant's rows
  hold results that must stay defensible. Trainees with a decision are
  anonymised, not deleted.
- **Temporary passwords and bootstrap admins.** No password passes through the
  app. The first admin is seated by address (`SeatMemberPanel`) and emailed a
  link; everyone else is invited by an org admin.
- **One sign-in**, not the four legacy B2B console logins.
- **Exam-mode supervisors cannot be heard or seen.** The observer token is
  subscribe-only in exam mode, so the transcript stays a record of the
  candidate. Training-mode supervisors may publish (since 2026-09-24).
- **S-2: A circuit's clock is never extended** for one candidate's
  `needs_extra_time`/custom timers (formerly `extra_reading_percent`, still on
  `users` for `app.migration` but superseded on the live API by A3); it extends
  their own practice only. A circuit has one clock for everybody on it. An
  institution grants extra time by putting the candidate on their own circuit
  with a longer `timing.reading_minutes`.
- **A station's scenario never reaches the browser before an attempt.** It is
  frozen server-side and read by the worker, so the station page is thin and
  reading happens inside the consultation. The org station list strips the
  patient's material for trainees (`stations/domain_content.py`).
- **Library stations are adopted by reference**, not imported as copies; a copy
  would go stale against the platform's next fix.
- **A community question's title is the first line of its body.** The backend
  takes a title; legacy had one box.
- **Station images are a plain `<img>`**, not `next/image`: their hosts are not
  configured, and an unconfigured host is a runtime error.
- **Not surfaced on purpose:** circuit `edit-lock` during a live exam (reads as
  a false warning), `recruitment_outcome` on exam results (belongs to hire),
  ranking on training circuits (`not_an_exam_sitting`), the inert cohort
  archive field.
- **AI practice differs from legacy on purpose in five places:** the exam
  date has no time (the column is a date); the end screen says "Couldn't be
  marked" where marking failed (legacy said "Not attempted"); which stations
  are "ready" is read from attempts on the server, not from jobs this browser
  started; the station table's transcript and feedback links open the
  station's own review tabs (there is no per-station transcript list); and
  legacy's `?preview=` demo modes on the complete page are not ported.
- **Not ported:** `confetti-check`, `features/[featureId]` (feature requests
  retired), the marketplace leaderboard (already off in legacy),
  `@stripe/stripe-js` (checkout redirects), the LiveKit timer data channel (the
  server owns the clock), the trainee pre-join state machine (`can_join`
  replaced it), feedback-template URLs (merged into rubric versions), and a
  service worker (legacy's `sw.js` only logged; the web manifest was ported as
  `app/manifest.ts`).
- **Called by workers and webhooks, never by a browser:**
  `/assistant-sessions/*`, `/attempts/{id}/transcript-chunks`,
  `/livekit-cloud-slot/*`, `/sessions/{id}/complete`,
  `/billing/webhooks/stripe`.
