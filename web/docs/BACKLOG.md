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
| Read a trainee group's members | Only `PUT /orgs/{org_slug}/trainee-groups/{group_id}/members` is served; there is no read, so screens resolve members through the roster |
| Whether a circuit's review was published | Only `POST /orgs/{org_slug}/circuits/{circuit_id}/review/finalize` is served. There is no read, so `CircuitFeedbackCard` says what it did rather than what is true |
| An examiner's own slot review | `PUT .../slots/{slot_id}/reviews/mine` is a write only; there is no read of one's own review, so screens find it in the slot's review list |
| A candidate reading their published review | No candidate-facing read of a circuit's supervisor review or their slot review. The largest thing the sittings port could not carry |
| Release decisions in bulk, notify candidates | Release is per candidate only; there is no bulk release and no notification |
| Cohort export (the markdown readout) | Not built. Low priority |
| Organisation hierarchy | `OrganizationRead` has no parent organisation |
| Live board history | `/orgs/{slug}/live` shows now only; nothing shows what ran this morning |

### Staff console (platform)

| Item | State |
|---|---|
| Directory search | `GET /platform/organizations` takes `status`, `cursor` and `limit` only. Search and the type filter run in the browser over the whole directory, which stops scaling in the thousands |
| Audit search | Per-organisation audit has no actor filter |
| Platform exam list | There is no list under `/platform/exams`; the console reads the unscoped `GET /exams` |

### Authoring

`capabilities/authoring/api/scope.ts` names the backend's asymmetries:

- Platform scope has no brief edit and no draft-version delete (see decision D4 below).
- Org station search takes no `?q=`.
- The template list has no cursor pagination.
- There is no "used by" count, so deleting a station cannot warn what it breaks.
- There is no delete for an exam or a template.

### Consumer (train)

| Item | State |
|---|---|
| Delete your own account | There is no delete route for `/me`. Needs a data-handling decision too |
| Upload your own profile photo | `PhotoUpload` has a real caller for station photos (`stations/router_photos.py`); nothing supplies an `upload` for a person's avatar. Reuse the station-photo route family |
| Referral history per referee | `GET /me/referrals` returns one aggregate row; there is no per-referee list |
| Referral payouts | The backend serves `POST /growth/referrals/{referral_id}/payout`, but the staff growth screens do not call it. Bank details have no storage |
| Voice onboarding scenes | No onboarding-scenes route in `assistant/`; needs design as well as code |
| Assistant cards | `parseAssistantCardPayload` (`foundation/livekit/guidance/contracts.ts`) has no receiver |
| Media specialty facet | Facets read `content.specialty`. `MediaRead.specialty` exists but nothing writes it; backfill, then switch |

### Peer practice

Protocol and schema work in `peer_practice`, none of it started:

- The two-minute decline-and-requeue handshake, and automatic requeue.
- Telling "partner left" apart from a dropped connection.
- Persisting `would_practice_again`.
- Real partner and poster usernames.
- A "partner unavailable" error code for the queue.
- Cancelling a booked marketplace session leaves the practice session it already opened
  running. Cancelling should end that too (`marketplace/service_sessions.py`).

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
| — | Preferences: AI-training consent, colleague-waiting email, onboarding replay. Only `extra_reading_percent` is stored | Decide which are worth storing |
| — | Push notifications. `web-push` is not a dependency, and legacy's service worker never sent one | Decide whether wanted at all |
| — | Consumer performance extras: RAG by domain, category volume, SCA trends, exam date | No data source exists for them; decide what to record first |
| — | Peer practice recording, transcript and AI feedback | Decide scope |
| — | Ortho CV upload | No decision on record |
| C-1 | **CASC is marked with the RCGP GP prompt**, on both scoring paths. No CASC marking prompt exists, and the engine maps `casc-rcpsych-v1` to the SCA prompt | This is live behaviour, so fixing it changes feedback real users are reading. It needs a prompt, plus a decision about existing feedback |
| B-3 | Referral discounts: b2c swaps to a discounted price id and credits the referrer a flat amount. Not ported | Codes are paused in the product copy. The price-id lookup already treats a discounted price as its own plan row |
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
  `extra_reading_percent`; it extends their own practice only. A circuit has one
  clock for everybody on it. An institution grants extra time by putting the
  candidate on their own circuit with a longer `timing.reading_minutes`.
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
