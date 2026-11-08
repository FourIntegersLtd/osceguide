# Backlog

The one list of pending work for the live stack (platform-web, platform-api,
assessment-platform): what it still does not do, and the few things it does
differently on purpose. It replaces `port-gaps.md`, `parity-fix-plan.md`,
`gap-closure-plan.md`, `ai-practice-b2c-parity-checklist.md` and platform-api's
`docs/OPEN-QUESTIONS.md` (removed 2026-09-25, recoverable from git history).
Rows with an ID keep it, so the code comments that cite one still resolve.
Don't start another list in another repo. Add a row here.

**Breakage list:** everything that breaks, misleads or dead-ends a user is in
`docs/EXPERIENCE-GAPS.md` at the repository root, with the fix loop in
`.claude/skills/fix-experience-gaps/SKILL.md`. Rows here that it absorbs carry its ID.

**Rules for this file**

- Only open work. When an item lands, delete its row in the same commit.
- Re-check a row in the code before scheduling it. The files this replaces
  drifted both ways: rows marked open that were built, and the reverse.
- `npm run ci` runs `scripts/audit-ledger-routes.mjs` over this file. A route
  named here as fact must exist in `openapi.json`; a route that does not exist
  must be written as missing ("there is no …").

Checked against the code on 2026-09-29.

## Open: engineering

### Authoring

`capabilities/authoring/api/scope.ts` names the backend's asymmetries:

- Programmes exist only for an organisation.
- A brief edit is org-only. Throwing away a station draft is both: the platform has `DELETE /platform/stations/{id}/versions/{n}`, and a station whose last version goes is deleted with it.
- Drafting a station from a prompt with no template is platform-only (`POST /platform/generate/station`). An organisation generates through its autogenerate-draft route, which needs a published template.
- A platform exam cannot be deleted; it is retired. An organisation's exam can (`DELETE /orgs/{org_slug}/exams/{exam_id}`, refused with `exam_in_use`). A template is removed only when its last draft version is deleted.

### Code quality audit leftovers (2026-10-01)

| # | Item | State |
|---|---|---|
| Q-1 | `StationScreen.tsx` still holds nine pieces of state | The leave guard and the station-source helpers were split out. Turning the rest into one step reducer needs a walk through a live station in a browser first, as there are no component tests |
| Q-2 | Three api files still name an exam in code | `assistant/content/packs/__init__.py` (per-exam wording belongs in the exam's data), `media_production/slide_av.py` and `slide_renderer.py`. Listed in `STILL_NAMES_AN_EXAM`, which only shrinks |
| Q-3 | `media_production/slide_renderer.py` (1,700 lines) is exempt from type checks | Leave it until it is next changed, then split it and type it |
| Q-4 | The mock screens other than `MockUpdate` load the whole station list to show titles | `MockEnd`, `MockDetail`, `SetStation` and `useMockWorkspace` should ask the server for only the stations they show |
| Q-5 | The assessment folder has no lint or type check in CI | Adding ruff needs a new Poetry dependency, which is the owner's call |
| Q-6 | Some `# noqa: BLE001` comments give no reason | `health/service.py`, `rubrics/service.py` and `app/migration/*`: say why the broad catch is right, or narrow it |
| Q-7 | Two-factor sign-in is switched off | The code was removed rather than left commented out. Whether it returns is a product decision |
| Q-8 | Peer practice session lengths now come from each exam's settings | Run `seed_platform.py --republish` on staging, then production, so PLAB 2, CASC and the orthopaedics exam get their own lengths. Until then they use the default lengths |
| T-1 | Free trial is two weeks everywhere | Study media unlocks for 14 days from `users.created_at` (`media/service_search.py`) while the trial counts from `activated_at` (`entitlements/domain.py`), so an invited person loses media days they never saw. Community, CV reading and the assistant's chat are not gated by the trial window at all: decide whether they should be. The marketplace and peer lists (browse) stay open to everyone; only joining is gated |
| Q-9 | Security report ids (`SEC-0xx`) remain in code comments | Kept on purpose: they point at `api/docs/security/SECURITY-ASSESSMENT-2026-09.md`. Drop them once the report is closed |

### Rubric templates (Stage 3 leftovers, 2026-09-30)

| # | Item | State |
|---|---|---|
| R-1 | Republish the 4 platform rubrics on staging, then production | `seed_platform.py --republish --env staging`, check the four feedback pages and dashboards, then `--env production`. A deployed write: owner's go-ahead |
| R-4 | `dashboard/` still sends legacy red/amber/green | The screens no longer read it. Removing it is optional platform-api cleanup |
| R-8 | Stage 4's staging exit | As a staging institution admin: copy PLAB 2, change the pass mark, add a field, publish, run an exam, see the candidate feedback and dashboard follow the edits |
| R-5 | `rubricView.ts` (328 lines) and `testRubrics.ts` (359) warn on max-lines | Split the view model by block kind if it grows |

### Backend and workers

| # | Item | State |
|---|---|---|
| M-1 | Consumer identity import needs a production export | The loader and verify step are written and proven against a real database (dry run, real run, idempotent re-run, tamper-detecting verify). The production export is still needed to size the run and find real-data shapes. Station sets, sittings and org data are not transformed yet |
| V-1 | The debrief clock and walk-through prompt are unproven live | Engine `engine-v0.8.0` (assessment-platform `fd5180b`) landed with platform-api `835d34e`; staging is now further ahead at `c004c8e` (see E-3). Run one staging debrief (`verify-attempt-engine`): the tutor walks the plan, never mentions time, and closes near 10 min. Then Promote the worker and platform-api together |
| V-2 | The debrief rarely reaches the differential | Missed in 14 of 16 bench debriefs even with the clock. The likely cause: each plan section opens by asking what the doctor told the patient, which a differential never is. A `differential` bench variant now changes only those sentences, and the report counts misses per heading. Run `scripts/debrief_bench.py run --variants baseline,differential --repeats 2` with real keys, then ship the variant if it wins |

### Website hosting

| # | Item | State |
|---|---|---|
| W-1 | Enforcing the CSP is still unproven | Middleware now mints a nonce per request and forwards it so Next can stamp its scripts. The policy still ships Report-Only unless `PLATFORM_WEB_CSP_ENFORCE` is set: a nonce policy forces dynamic rendering, and a page that stays static fails closed (blank page, found on staging 2026-09-26). Prove the whole journey on staging before setting the variable |

### Canvas screens with no backend (2026-10-03)

Board elements in the quiet canvas (claude.ai/artifact/N1BqEe2yaLUbht9ePqt7xZ) that the API cannot feed. They are left out of the build, not faked. `field` means add to an existing response, no migration. Delete a row when the backend lands and the UI is built.

| # | Screen | Missing element | Needs |
|---|---|---|---|
| U-1 | Overview | Stations sat today tile; Every arm counts; attention items for station reports, failed Stripe updates and voice capacity | field; affiliates and white label also need a route |
| U-2 | User detail | Sign in as (there is no impersonation route); attempts table station name, score, band | route and auth decision; field |
| U-3 | Attempt | Station name and user name in the title and back link; event timeline (only timestamps exist) | field |
| U-4 | Organisations | Members column; Employer type (the API accepts institution and partner only) | field; migration |
| U-5 | Organisation detail | Seats used, sittings this year, stations sat; exam access; bonus pool and gift credits panels | field; migration and route for credits |
| U-6 | Create organisation | First admin's email and contract end date on create (there is no bootstrap-admin route) | route and field |
| U-7 | Team | Role and two-factor columns | field |
| U-8 | Billing | Four-stat strip (taken, refunds, failed, payouts); Stations column on prices | route for aggregates; field |
| U-9 | Payouts | The board is a Stripe Connect payout run (payee types, Stripe status, due dates, batches, rules, second approval, confirm page). Today's page is a manual bank ledger that shows bank details the board says we never store | migration, route and product decision |
| U-10 | Affiliates, affiliate detail, white label | All three screens (no models, no routes) | migration and route |
| U-11 | Growth | Sign-ups by week chart, partner fee stat | field |
| U-12 | Machinery | Deploy sha and age; patient workers n of m and longest wait; email outbox and failed-today counts; tutor index documents and last rebuilt | field |
| U-13 | Audit | Names instead of emails; readable targets | field |
| U-14 | Media item | Locked for trial users setting (lock is computed per reader); specialty select | migration; field |
| U-15 | Messages | Tab counts; star rating and may-quote-with-name | field; migration |
| U-16 | Moderation | Flagged by N users, Keep action, flagged-only list (posts have no flag entity) | migration |
| U-17 | Assess and hire | Programme purpose and detail pages; trainee programme view (the mock screens were deleted 2026-10-06; build them on real routes); self-serve organisation sign-up; organisation settings and SSO tabs; shared review | migration and route |

## Open: enterprise readiness

What an institution's procurement and IT security review will ask for and we
cannot yet show. Checked against the code on 2026-09-29. Everything here is
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
| E-1 | Owner | SEC-012: rotate exposed credentials | The only **Open** High in `api/docs/security/SECURITY-ASSESSMENT-2026-09.md`. Four TLS/LiveKit keys (`misc/*.pem`) and a GCP `serviceAccountKey.json` still sit in the workspace, plus a GitHub credential in history and a GitHub token written into platform-web's local `osceguide-frontend` remote URL (`git remote -v`). Revoke each at its provider, move them to a secrets store, purge history, turn on secret scanning. Done when old credentials are refused |
| E-3 | Eng | Erasure and data download are on staging only | Staging API at `c004c8e` (2026-09-27). Local erasure script proved `erase_due_accounts` scrubs PII after 30 days. Still to do: download export on staging in a browser, confirm `erase_closed_accounts` ran in Railway worker logs, then Promote platform-api and advance platform-web `production` to `654dfb50`. The privacy policy now describes this, so production is behind its own policy until then |

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
| E-17 | Owner | SLA and support terms | No uptime target, support hours or incident-notification promise is written down. Contracts will ask |

### Tier 3: when a deal asks

| # | Who | Item | State |
|---|---|---|---|
| E-19 | Owner | Accredited external pen test | The current report is white-box, local-only, not CREST-accredited, and did not test production. Larger buyers will ask for an accredited test of the deployed service |
| E-24 | Eng | Tamper-evident audit | `audit_log` is append-only by convention (no `updated_at`), not enforced. Revoke UPDATE and DELETE on it from the app's database role |
| E-25 | Owner | ISO 27001 or SOC 2 | Only when a contract requires one. Months of work and ongoing cost |
| E-26 | Eng | Metrics | No Prometheus or OpenTelemetry. Sentry and logs are enough until an SLA needs measuring |

## Open: needs a product decision

| # | Question | Recommendation on record |
|---|---|---|
| D2 | A released result now includes the 0–100 score (`GET /me/results/{sitting_id}`). Show it against a pass threshold? | A threshold is not stored on the decision, so the API does not send one. Keep that until an examiner sets a bar |
| D4 | Platform stations have no brief edit, and programmes are org-only. Platform template drafts can be deleted | Keep unless staff actually author briefs |
| D7 | Adding a candidate to a live **exam** circuit is refused (`not_permitted_in_mode`), as legacy did | Confirm. A second candidate means one room, one clock and one transcript marked as one doctor's |
| D8 | Deleting a practice set that has been sat is refused (`set_has_attempts`); legacy orphaned the recordings | Keep. Self-service deletion would be its own audited action |
| D9 | Deleting a non-empty group or in-use cohort is refused | Keep. Residual hole: a cohort that only scheduled sittings is deletable and detaches them |
| D10 | A re-sent invitation spends the previous unused link | Confirm supersede; keeping the old link live is a one-line change |
| — | Live marking: a rubric a supervisor fills **during** a consultation, independent of machine scoring (a live exam now ticks the active station in `LiveMarkPanel`; a finished station is marked from Station progress) | Out of scope until wanted; it is a redesign against `marking_layout` |
| — | Preferences: AI-training consent, colleague-waiting email, onboarding replay | Decide which are worth storing |
| — | Push notifications. `web-push` is not a dependency, and legacy's service worker never sent one | Decide whether wanted at all |
| — | Consumer performance extras: RAG by domain, category volume, SCA trends | No data source exists for them; decide what to record first. `exam_date`/`exam_time` are now stored (A4) and read on `UserRead` |
| — | Peer practice: production promotion and two follow-ups | Proven on staging 2026-09-27 (session bc0e13de): match, preparation with a real station, consultation, recording, transcription (5 turns), marking and the doctor's "AI feedback is ready" page. Two fixes found on the way, platform-api 431bfa3 (recording creates the room first) and b6538bf (marking accepts doctor/patient turns), are on staging only: production needs the Promote workflow. Marking in that run needed a support rescore after b6538bf deployed, so the next staging session should confirm it marks unaided. Open: the matcher pairs people when an exam has no published stations (should refuse); the partner's video tile was black 20 s into the consultation (may be the fake camera) |
| — | Ortho CV upload | No decision on record |
| C-1 | **CASC existing databases still mark with the RCGP GP prompt.** A CASC prompt now exists (`api/seeds/prompts/casc_system.txt`, 2026-09-26; b2c never had one, it fell back to SCA) and the seed uses it, but `seed_platform.py` never touches an exam that already exists | Publish a new CASC rubric version carrying the new prompt on staging and production (a deployed write: owner's go-ahead). Existing CASC feedback stays as it was marked |
| B-3 | Referral discounts are built (checkout swaps to the `<plan>_referral` row, the webhook credits £2.50 / £5), but no environment has the 10%-off Stripe prices or `_referral` plan rows yet | Create them per exam after the code deploys; before that, a code at checkout is refused `referral_discount_unavailable` |
| R-2 | Sign-off requires an outcome and a rationale; the proposal also wanted full "readiness" for a pass or fail, and no readiness concept exists | Decide whether readiness is a real gate or drop it from the invariant |
| T-2 | A templated station contributes nothing to the tutor's material index: its blocks are all patient-private or expected answers | Needs a template block role that means "reading material" before any code |
| T-5 | Help articles reach Athena's index only on the nightly reindex (or the admin route), so a help-text deploy is stale until 03:17 | Reindex the help corpus on deploy, or trigger the admin route from the deploy workflow |
| T-6 | Athena everywhere is unproven in a browser and on staging | After the monorepo deploy (migration `v3w4x5y6z7a8` rides with it), run the admin reindex, then walk the plan's Stage E (consumer and institution admin). Also walk topic mode: "Discuss with Athena" on a summary, a deck, an episode and under a typed knowledge answer opens the call on that subject, she answers from the material, and says so when it has nothing |

## Not gaps: do not re-report

Each is deliberate and explained in the code where it lives.

- **Tenant and account hard delete.** Suspend is the mechanism; a tenant's rows
  hold results that must stay defensible. Trainees with a decision are
  anonymised, not deleted. A person closes their own account with
  `POST /me/close`; sign-in stops and a job erases the personal data later.
  There is no hard delete of `/me`.
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
  with a longer `timing.reading_minutes`. A supervisor can lengthen that shared
  phase with `POST /orgs/{org_slug}/circuits/{circuit_id}/extend-clock`; it
  still moves everybody on the circuit.
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
- **Not surfaced on purpose:** ranking on training circuits (`not_an_exam_sitting`), the inert
  cohort archive field. The live console hides Edit when the circuit cannot be
  rebuilt, and the edit screen says why (`editable` / `edit_block` on the
  console frame). It does not call `GET /orgs/{org_slug}/circuits/{circuit_id}/edit-lock`
  on its own.
- **AI practice differs from legacy on purpose in four places:** the end
  screen says "Couldn't be marked" where marking failed (legacy said "Not
  attempted"); which stations are "ready" is read from attempts on the server,
  not from jobs this browser started; the station table's transcript and
  feedback links open the station's own review tabs (there is no per-station
  transcript list); and legacy's `?preview=` demo modes on the complete page
  are not ported. The exam date and time are both stored.
- **Not ported:** `features/[featureId]` (feature requests
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

## Institution walkthrough 2026-10-06: decisions and what is still open

- R-2 (decided): signing off while station reviews are incomplete is allowed; the candidate rail shows "Reviews not complete" as an attention step. No API readiness gate.
- Open, needs staging: live consultation, real automatic marking (score and review-priority columns), email delivery of the result notice.
