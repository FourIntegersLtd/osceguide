# Parity fix plan — status and handoff

**Purpose:** this file is a complete handoff. A fresh session with no conversation
history should be able to pick up the work from here alone. Read it top to bottom
once, then work the first unchecked phase.

Audited against the retiring client on 2026-09-23; the audit's verdict was that
~85% of legacy B2B+B2C behaviour had a live counterpart in `platform-web`, with
ten things actively **broken** (section A), thirteen capabilities never ported
(B), two dozen screens materially degraded (C), and a set of backend routes
served but uncalled (D).

---

## 0. Baseline, and how to verify it

Two **separate** git repos. The workspace root is **not** a repo.

| Repo | Branch | Baseline commits |
|---|---|---|
| `platform-web/` | `master` | `83ddcd2` (ten A-section defects + Phase 1 first half), `c9d070e` (Phase 1 second half) |
| `backend/` | `main` | `2c5f9d1` (community author-name join, single-question read, `service_reads.py` split) |

Nothing has been pushed. **Do not push** unless asked.

### Commands

`node`/`npm` are nvm-managed and are **not on the PATH of a non-interactive
shell** — they are also not on the PATH of this agent's shell tool. Prefix every
Node command or it fails with `command not found` while still looking like a
clean run:

```bash
export PATH="/Users/yahayakenny/.nvm/versions/node/v22.22.3/bin:$PATH"
cd platform-web && npm run ci        # = types && lint && test
```

```bash
cd backend/platform-api && make ci   # = lint typecheck arch guards test status-check
```

### Three failures that are NOT breakage

1. `tests/contract/test_engine_adapter.py::test_the_engine_only_needs_pydantic`
   — red at clean `HEAD`, and still red for the whole file today (verified: the
   file is untouched since `aa0a1b0`). "Passes alone" needs the precise sense: it
   passes when selected **by test id** (`pytest "tests/contract/test_engine_adapter.py::test_the_engine_only_needs_pydantic"`
   → 1 passed) and fails when the **file** runs, because the seven engine tests
   above it import the real `osce_assessment`, which pulls `openai`, and the
   assertion reads `sys.modules`. So an isolated run of this file is *not* proof
   of a new breakage — select the id.
2. `tests/http/test_assistant_routes.py` and `tests/http/test_voice_routes.py`
   assert un-prefixed `agent_name`s. A local `.env` sets
   `LIVEKIT_AGENT_NAMESPACE=local-yahaya`, which makes them fail. Run with
   `LIVEKIT_AGENT_NAMESPACE=` to clear it. Verified: both pass with it cleared.
3. Backend suite takes ~10 minutes whole and exceeds a 10-minute shell cap. Run
   it in chunks (`tests/unit tests/guards`, then `tests/http`, `tests/contract`,
   `tests/repository`, then `tests/migration` **alone** — it fails with 5 errors
   only when run after `tests/repository`). DB tests need the docker
   Postgres/Redis from `docker-compose.yml`; without them they silently skip and
   a "pass" means nothing.

Current real state, after Phases 2 and 3's backend half (2026-09-23). **Backend —
fully verified, re-run to completion this session:** `lint`, `typecheck` (511
files), `arch` (2 contracts kept), `check_data_model.py` and `status-check` all
clean; by chunks **5305** passed in `tests/unit` `tests/guards`, **685** in
`tests/http` with only the two namespace artifacts red (**11 pass** with
`LIVEKIT_AGENT_NAMESPACE` cleared), **238** in `tests/contract` `tests/repository`
with only the `test_the_engine_only_needs_pydantic` order artifact, and **77** in
`tests/migration` run alone — ~6,300 passing, only the two documented artifacts
red. So criterion (4) is met.

**Web — count is mid-flight, do not trust the number below until the screen
agents land.** Phase 2 closed at `types` 0 errors, `lint` 0 errors / 72 warnings,
**228/228**, `npm run build` green with `/staff/station-flags` in the route list.
The sittings/examiner agent (done) added 11 tests → **240 pass, 0 errors**; the
consumer-stations and roster-team agents are still writing tests, so re-run
`npm run ci` after they land for the authoritative figure. `check:ledger` is at
**135 mentions agree**.

---

## 1. House rules that will bite you

- **Import tiers, enforced by eslint**
  (`app → surfaces → domains → capabilities → foundation`). A capability may not
  import a domain or a surface. A **surface may import any domain** — that is how
  the institution arm renders Train's practice sets without forking them. A
  domain may import only its own arm's domain, capabilities, and foundation.
- **250 lines per `app/**` python file**, enforced by
  `tests/guards/test_slice_shape.py`. One documented exception. When a slice
  service outgrows it, split by concern the way `community/service_reads.py` and
  `stations/service_reads.py` do — writes+visibility in `service.py`, projections
  in `service_reads.py`.
- **Adding a response model:** grep every other slice for the same class name
  first. Two Pydantic models sharing a class name makes FastAPI qualify **both**
  component names, which silently renames a type `schema.d.ts` already imports
  and breaks `tsc` web-side with nothing web-side changed. This has happened
  (`peer_practice` vs `attempts/schemas_material.py`, fixed by prefixing).
- **After any backend schema change:** `make openapi` → `npm run platform:types`
  → `npm run types`. Regenerate centrally, never from parallel agents —
  `schema.d.ts` is one shared 835 KB generated file and two sessions writing it
  collide.
- **Strict types, no `any`** (lint error). An API call goes in the owning slice's
  `api.ts` via `platformRequest`; never a bare `fetch`. Branch on
  `PlatformError.code`, never on `message`. Loads go through `useAsync` +
  `AsyncBoundary` so a failure can never render as "no data". Colours come from
  tokens, never a literal `bg-blue-600`.
- **Route files hold no logic** — they read `params`/`searchParams` and hand them
  to `<Screen name=… />`. Which component answers comes from the arm's screen map;
  an arm that does not declare a screen name 404s. Adding an arm adds no routes.
- **Ports must match the legacy screen**, not improve on it. Where the legacy
  screen exists, read it before writing (`frontend/src/b2b/**`,
  `frontend/src/b2c/**`). New arms with no legacy equivalent are exempt.
- **`platform-web/docs/port-gaps.md` is a duty, not a graveyard** — see §6.
- This Next.js version is **not** the one in training data. `platform-web/AGENTS.md`
  demands reading `node_modules/next/dist/docs/` before writing route or
  server-component code.

---

## 2. Phase 0 — DONE

Baseline committed and green. Two operational hazards recorded: the tree was
being edited concurrently by other sessions, and `schema.d.ts` changed mid-audit.

### Product decisions still open

These are all written into the code as *deliberate*, with in-source justifications.
Do not "fix" one by reflex — confirm or reverse it.

| # | Decision | Where it is written down | Recommendation |
|---|---|---|---|
| D1 | Supervisor mic/camera + video grid. `observer-token` is minted `can_publish=False` unconditionally (`sittings/service_join.py:76-101`); `voice/README.md:42-45` calls it "a guarantee, not a UI state" | **done 2026-09-24** — reversed for training mode only; see §8 below |
| D2 | Trainee result narrowing — `MyResult.tsx:10-19` says the omission is disclosure policy | keep, but add score-vs-threshold where the outcome is already released |
| D3 | Per-sitting feedback-template choice — `NewSitting.tsx:142-143`: rubric comes via programme | keep; record as a decision, not a gap |
| D4 | Platform-scope authoring has no brief PATCH / draft DELETE / programmes — `capabilities/authoring/api/scope.ts:41-42` | keep unless staff actually author briefs |
| D5 | Feature-request admin retired — `legacyRedirects.ts:226` sends `/features/**` to `/` as "superseded" | confirm retired |
| D6 | No PWA. **Verified fact:** `frontend/public/manifest.json` never existed and `frontend/public/sw.js` is 38 lines of `console.log` with every push handler commented out. There was nothing to port | confirmed; `app/metadata.ts:10-21` documents it |

Surfaced by the Phase 3 build-out (2026-09-23) — the implementer took the safe
branch each time; each still needs a product owner to confirm or reverse:

| # | Decision | Recommendation |
|---|---|---|
| D7 | **Append a candidate to a *live exam* circuit is refused** (`not_permitted_in_mode`). This matches the retiring backend (`circuit_service.py:311` — training only, "use Edit circuit for exam sessions"), and an exam circuit is one candidate by construction: a second person means two in one room, one clock, and **one transcript marked as a single doctor's**. | confirm the refusal (it is parity, not drift); a mid-exam addition needs a grading/disclosure design, not a flag |
| D8 | **Deleting a practice set that has been sat in is refused** (409 `set_has_attempts`). Legacy deleted the mock and silently orphaned the recordings. The `attempts.set_entry_id` FK is `RESTRICT`, so deleting anyway means a migration or a self-service attempt-deletion route. | keep the refusal; if self-service deletion is wanted, build it as its own audited action like the console's `delete-progress` |
| D9 | **Deleting a non-empty group / in-use cohort is refused** (409 `group_not_empty` / `cohort_in_use`). Legacy deleted a label the roster still pointed at; a group is also the `ondelete=CASCADE` target of `community`/`marketplace`/`peer_practice` audience rows, so an unconditional delete would take other slices' content. | keep; the known residual hole is `sittings.cohort_id` (`SET NULL`, and `sittings` sits above `roster`) — a cohort that only scheduled sittings is deletable and detaches them; fixing it needs the guard moved into `sittings` or a seam in `main.py` |
| D10 | **A re-sent invitation mints a new token and spends the account's previous unused tokens.** Legacy's `regeneratePassword` also superseded the link, so superseding is the closer port — but the old link then 404s for anyone mid-click. | confirm supersede; keeping the first link live is a one-line change if support prefers it |

Two Phase 3 items first listed as "deferred for a decision" are **closed by
evidence, not by a ruling** (2026-09-23):

- **Library import — was never a gap.** Re-read the retiring client:
  `StationLibraryModal` → `OSCEGuideStationLibraryTable` → `StationDetailPanel`
  has no write at all (no POST, no add, no import anywhere in `b2b/lib/stations/`),
  so the modal never copied a station either. Adoption here is by reference:
  `core.ownership.visible_to` returns "its own, plus the platform library", and
  `StationLibrary` — mounted at `/app/[workspace]/stations` *and* inside
  `CircuitBuilder` — puts a library station straight onto a circuit. A copy would
  go stale against the platform's next fix, which is the one thing an "import"
  exists to avoid. So no route was created, deliberately.
- **Exam-mode `append-trainees` — the refusal *is* the parity.** The retiring
  backend refuses it outright (`b2b-api/app/features/sessions/circuit_service.py:311`:
  "only supported for training circuits. Use Edit circuit for exam sessions"), and
  an exam circuit is one candidate by construction — a second means one room, one
  clock and one transcript marked as a single doctor's. What an exam *sitting*
  supports is another candidate as another circuit, and `POST /sittings/{id}/circuits`
  already works mid-sitting with `NewCircuit.tsx` mounted as a screen. The refusal
  is surfaced, not swallowed (`not_permitted_in_mode` is code-mapped in the
  dialog). Building around this would diverge from the acceptance rule, so it is
  left as legacy had it and recorded here rather than asked.

**Image upload** remains genuinely open — it needs an object-storage decision
(bucket, lifecycle, sizing) that no code choice can substitute, and
`foundation/ui/PhotoUpload.tsx` is still dead for exactly that reason.

---

## 3. Phase 1 — DONE (all nine, committed `83ddcd2` + `c9d070e`)

| Item | What shipped |
|---|---|
| 1.1 Template-less station creation | dropped `disabled={published.length === 0}` in `capabilities/authoring/sections/StationsSection.tsx`; the backend precondition was already gone and `useCreateStationForm.ts:118,155` already asks which exam |
| 1.2 Editable profile name | `settings/ProfilePanel.tsx` now writes via the existing `updateMe`, and calls `session.refresh()` too — `StaffNavFooter`/`TrainNavFooter` print `session.user.name` |
| 1.3 Circuit breaks | new `domains/assess/timing.ts` (+5 tests) mirroring the server: **exam mode only**, one shared `break_minutes` (1–60), never after the last station. Legacy's per-break duration deliberately **not** ported — nothing reads it |
| 1.4 Practice sets on the assess arm | 4 names in `ASSESS_SCREEN_NAMES` + 4 adapters in `surfaces/assess/screens.tsx`; `hire` inherits automatically |
| 1.5 Install prompt | mounted in `app/layout.tsx`; consent exclusion via `hasAnsweredAnalyticsConsent()` reading the shared key. Also corrected a comment that claimed a gate `appType = null` made inert |
| 1.6 `/cv/{id}` | `readCv(id)` in `capabilities/account/api.ts`; `CvPanel` follows the uploaded row by id instead of re-listing every 5s |
| 1.7 Privacy policy | Mixpanel removed from `app/(public)/compliances/privacy-policy/page.tsx` (GA was already listed; the product ships no Mixpanel) |
| 1.8 Dead script | deleted `scripts/ensure-legacy-frontend-node-modules.mjs` (self-referencing only; no `prebuild` invokes it) |
| 1.9 Join deep link | `/b2b/trainee/join/<slotId>` → `/app/me/trainee?slot=<id>`, resolved by `sittingForSlot`/`slotById` in `domains/assess/trainee/support.ts` against `MySitting.slots`. No new endpoint |

Also folded a **third** copy of the station `tab`/`action` parser into
`stationStepFromParam` / `stationActionFromParam` in
`capabilities/station-runner/useStationUrl.ts`, beside the writer.

**Loose end worth 5 minutes:** `sittingForSlot` and `slotById` have no direct
unit test — only the redirect assertion covers them. `support.test.ts` already
has `sitting()` / `slot` fixture builders to reuse.

---

## 4. Phase 2 — DONE (integrity fixes)

Three places where the product misrepresented its own state. All three are now
true, each with a test.

| Item | What shipped |
|---|---|
| 2.1 Station flags | A `station_flags` table (migration `j1k2l3m4n5o6`), deduped `(station_id, user_id)` with `status`, `resolution_note`, `resolved_at`. The route left `identity` (where it was `_ = principal; _ = body`, "Persistence is TODO") and lives in `stations` now: `router_flags.py` + `service_flags.py` + `repository_flags.py`. `POST /me/station-flags` is 204 **and idempotent** (legacy answered a repeat tap with 400, which the client surfaced as a failure over a report that had landed); `GET /me/station-flags` carries the station title, because the legacy screen resolved titles by listing every station it could and printed "Unknown Station" for anything off the page. `GET /platform/station-flags?status=open` + `PATCH .../{id}` are the staff queue. Web: `StationChrome`'s button now works — its body was double-encoded (`JSON.stringify` into a client that stringifies), so the request never reached any handler — plus a **"Flagged Stations" tab** in `domains/train/mocks/Mocks.tsx` (`FlaggedStations.tsx`, the legacy tab, same two columns and the same empty-state sentence) and a **staff queue screen** at `/staff/station-flags` (`domains/platform/StationFlags.tsx`, registered as the `stationFlags` screen). Tests: `tests/http/test_station_flags_routes.py` (10). |
| 2.2 Revision control on decisions | `SaveDecision.expected_revision` (`0` = "I have read nothing"), `domain.ensure_current`, and `decision_revised` (409, with `details.current_revision`) — the same rule the GP lead's review already had. Sign-off and release are unchanged: they were already guarded by the workflow state and the evidence fingerprint. `CandidateDecision.tsx` sends what it read, and on 409 shows "This decision has changed since you loaded it" with a **Load the latest version** button rather than quietly discarding the words typed. Tests: `test_a_save_against_a_revision_you_never_read_is_refused`, three in `tests/unit/test_results_domain.py`. |
| 2.3 `ready_to_run` | `OrgCounts.library_stations` (published platform stations **for the exams this org offers**, via `catalog.org_exam_ids`) and `OrgSetup.stations_authored` → `stations_available = own > 0 or library > 0`, which is also what `ready_to_run` now gates on. The dashboard step reads "Have stations to run". Tests: `test_a_library_only_institution_is_told_it_is_ready`, `test_the_library_counts_only_what_is_published_for_an_exam_offered`, and the `setupSteps` case in `support.test.ts`. |

Also landed from §5 while the queue was open: **`POST /admin/tutor-memory/reindex`
has a caller** — a "Rebuild now" section on `/staff/ops` that reports
sources/passages/retired, replacing "wait for tonight's run".

Docs updated as part of the work: `stations` and `results` slice READMEs,
`docs/DATA-MODEL.md` (+ the table count), `docs/STATUS.md` regenerated,
`openapi.json` and `schema.d.ts` regenerated centrally.

### Phase 3 — backend DONE, screens outstanding (2026-09-23 checkpoint)

Every Phase 3 route is written, tested and present in `openapi.json` (274
paths), and the central regeneration pass has been run: `make openapi` →
`make status` → `npm run platform:types`, with `tsc` clean. Roster: `PATCH`
trainee / trainee-group / cohort, `DELETE` group and cohort,
`POST …/resend-invitation`, and `POST /memberships/bulk` (placed in `tenancy`,
where staff actually live). Stations: `GET /stations/{id}`,
`GET /stations/{id}/versions`, `?search=` on the browse route. Station sets:
`PATCH` and `DELETE /me/station-sets/{id}`. Sittings: `PUT /sittings/{id}` (a
PUT with partial semantics, matching both legacy and `PUT /circuits/{id}`),
`GET /sittings/{id}/readout` (JSON, served by `dashboard` because `reviews`
sits above `sittings`), and `AppendTrainees.station_version_ids`. Examiner
transcript and result access widened to the supervisor named on the attempt's
circuit and nothing broader — through a bound seam (`attempts` declares
`bind_slot_supervisor_lookup`, `sittings` implements it, `composition.py` ties
it) rather than a second cross-slice import.

**Outstanding, in order:** (1) call each of those routes from a screen — the
twelve are the library per-station read (delete `findLibraryStation`'s
page-walk), `?search`, the version-history view, set rename and delete, the
trainee / group / cohort edit sheets, resend-invite, bulk team invite, the
sitting edit form, the read-out export, the append station target, and the
examiner's transcript read; (2) re-run `npm run ci` afterwards; (3) the ledger
pass in §6, now including the `port-gaps.md` rows at ~642–662 and every "wired
when platform-api serves it" row.

**Caller-gap CLOSED 2026-09-23.** `GET /api/v1/stations/{station_id}/versions`
was the one route at risk of shipping with no caller — the brief told its agent to
skip it if it needed a new home. It did not skip: `listStationVersions` in
`capabilities/stations/api.ts` is mounted by
`capabilities/authoring/sections/StationVersionHistory.tsx` as a lazily-read
disclosure in the authoring station view, and `check:ledger` (136 mentions) passes.
The consumer agent's other three landed too: `readLibraryStation` (the page-walk
`findLibraryStation` is deleted), `?search=` sent to SQL with commit-on-submit,
and `renameSet`/`deleteSet` on the session card. What is still gated is the
roster/team agent alone.

**All six Phase 3 screen-wiring agents have landed, and every route is now
proven to have a caller** — checked in source, not from a report: each api
function resolves to a `.tsx`, and each of those components is mounted on a
reachable screen (`SittingEditForm`←`SittingDetail`, `ReadoutExport`←
`CohortRanking`, `AttemptTranscript`←`SlotReview`, `AddTraineesDialog`←
`CircuitRunner`, `TraineeEditDialog`/`TraineeRowActions`←`TraineesPanel`,
`GroupEditDialogs`←`GroupsPanel`, `CohortEditDialogs`←`CohortsPanel`,
`BulkInviteDialog`←`InvitePanel`, `SessionCardActions`←`MockSessions`,
`StationVersionHistory`←authoring `StationDetail`, `FlaggedStations`←`Mocks`,
`StationFlags`←`/staff/station-flags`). `npm run ci` is green on the finished
tree (**0 errors, `# fail 0`, 254 tests**) and `npm run check:ledger` passes at
**138 mentions**.

Two follow-ups this surfaced, neither blocking:
- **`AsyncBoundary` never renders `empty` for a `null` loader result**
  (`foundation/ui/AsyncBoundary.tsx:47` returns early on `null`), so the
  "could not find that station" `empty` prop was already dead code and a dead
  link rendered a blank page. Worked around per-consumer; the one-line
  foundation fix would repair every other screen carrying a dead `empty` prop.
- `capabilities/community/{api.ts:56,QuestionDetail.tsx:36}` still name
  `findLibraryStation` in doc comments; the function is deleted, so those two
  sentences are now misleading.

Resumable state, all verified this session:
- `npm run ci` was green at the end of Phase 2 (`# fail 0`, 228/228) and
  `npm run build` succeeds with `/staff/station-flags` in the route list;
  nothing escapes `platform-web` (`@/b2b` survives only inside prose comments).
- `make ci` has **not** been re-run whole since Phase 2 landed; the targeted
  runs pass (`tests/http/test_results_routes.py`,
  `tests/http/test_org_read_models.py`, `tests/http/test_station_flags_routes.py`,
  `tests/unit/test_results_domain.py` = 60 + 10 passed), plus `ruff`, `mypy`,
  `lint-imports`, `check_slice_readmes.py`, `check_data_model.py` and
  `status_report.py --write`. Run the suite in the chunks §0 lists before
  believing it.
- `docs/port-gaps.md` was corrected for: station flags, the decision revision,
  `ready_to_run`, the Mocks tabs, Achievements' route, the profile
  name/preferences/exam-date rows, the locked-read upgrade path, the four
  community rows, the members/audit + platform-admins + at-risk + contract-date
  rows, and the reading-brief section. **Still stale, in this file:** the
  table rows that say a route is wired "when platform-api serves it" —
  `POST /platform/users/{id}/reset-password`, `GET /platform/users/{id}`,
  `Page_DirectoryUser_` search params, `OrganizationDetail.tsx`'s member/audit
  pair (all served today), `GET /api/v1/stations/{station_id}` and the library
  search row (pending on the agents), and `gap-closure-plan.md` §Phase 3's
  B4/B5/B6/B7/B8/B9 bundles, which list much now-served work as future.
- Phase 4, assessed and **not** started: `parseAssistantCardPayload` is not
  dead code waiting for a barrel entry — the backend produces both card kinds
  (`tutor_memory/service_tools.py:153` "suggestion" with
  `{ref,title,reason}`, `service_search.py:127` "citations" with
  `[{n,title,section,ref}]`), the worker passes them through unchanged, and
  nothing in `src` consumes them; the receive path is
  `foundation/livekit/guidance/useUiGuidance.ts` (see the
  `parseGuidanceProgressPayload` branch at :76). Image upload, referral
  payouts + bank details (needs a security review first), moderation flags for
  community content, consumer voice onboarding, partner-attribution revenue
  routes and the in-session rubric sidebar each need a design or product
  decision and are reported blocked, not deferred silently.



---

## 5. Phases 3–5 — see the end of the audit trail

**Phase 3, backend-enabled assess/authoring parity (~8–10 days).** Each needs a
route then its screen:
`PUT/PATCH /sittings/{id}` + cohort readout export (`SittingDetail.tsx` is still
86 lines; zero "readout" endpoints exist) · `AppendTrainees` station target
(`sittings/schemas.py:166-167` is `trainee_ids` only) and an exam-mode append path
(`domain.py:182-186` refuses all non-training) · `PATCH /trainees/{id}`,
trainee-group PATCH/DELETE, cohort rename/delete, bulk staff create,
resend-invitation (only `POST /trainees`, `/trainees/bulk`, `/trainees/{id}/access`
exist) · `GET /stations/{id}` + `/versions` + a `search` param (the table filters
≤25×100 rows in memory) + a library-import route · `PATCH`/`DELETE
/me/station-sets/{id}` (`station_sets/router.py` is GET/POST only) · **examiner
transcript access is an authorisation change, not a UI gap** — `GET
/attempts/{id}/result|/transcript` are owner-or-platform-admin, so an examiner
cannot read a candidate's transcript at all.
Already done, do not redo: `MembershipRead.email`, trainee CSV bulk import, bulk
"Release all" with per-candidate refusals, release notification email
unconditionally enqueued (`results/service.py:183-190`), `AttemptResult`
duplication removed.

**Phase 4, new subsystems (~10–14 days, needs design passes not ports).** Image
upload (backend has exactly **one** multipart route, `POST /cv`;
`foundation/ui/PhotoUpload.tsx` is dead code with an `upload` prop nobody
supplies) · referral payouts + bank details (**zero** `payout`/`bank_details` in
platform-api; needs a security review before code) · partner attribution (legacy
had ~18 views, `staff-growth/api.ts` has 3 calls; `growth/router.py` has no
revenue/anomalies/reconciliation/pilot-config/arrivals-list endpoints) ·
moderation flags (**no flag concept exists in the backend at all**) · consumer
voice onboarding (no flow, no `/onboarding-scenes` route) · assistant cards
(`parseAssistantCardPayload` in `foundation/livekit/guidance/contracts.ts:163-175`
has no consumer and is not in its own barrel) · in-session rubric sidebar
(supervisor marking is off-page via `StationProgressList.tsx:66-67`; trainee side
is entirely absent — `JoinRoom.tsx` is VoiceRoom + clock + Leave) · admin
tutor-memory reindex (`POST /admin/tutor-memory/reindex` still has zero callers;
one button in `/staff/ops`).

**Phase 5, docs.** See §6. Plus two verification holes:

- **Self-containment — now demonstrated, not just static (2026-09-23).** A
  `git worktree` of `platform-web` at `abe252b` — which contains no sibling
  `frontend/` or `backend/`, because `platform-web` is its own repo — built
  green: `npm run build` exit 0, full route list emitted, and a grep for any
  import escaping the tree (`@/b2b`, `@/shared`, `../../frontend`) returned
  nothing but the two prose/comment mentions. The `node_modules` was a symlink
  into the real checkout and was removed as a link, not followed. This closes
  the "never demonstrated" half of the hole for the committed baseline; a
  checkout that omits `frontend/` in CI would still re-prove it on every change,
  and remains the right place for the standing check.
- **Browser parity harness — still open.** There is no Playwright spec and
  `scripts/smoke.mjs` needs a live `platform-api`, so "exact visual/UX match with
  legacy" — the stated acceptance rule — is still unmeasured by any automated
  check. Closing it means a real browser suite against both clients, which is
  new-infra work, not a port, and needs a decision on where it runs (CI budget,
  which browsers) before code.

---

## 6. The ledger drifts in one direction

**Run `npm run check:ledger` first, then read.** `scripts/audit-ledger-routes.mjs`
checks every `METHOD /path` named in the two ledgers against `openapi.json`, and
fails only when a route is asserted as fact while absent (a sentence that
proposes or denies a route — "there is no…", "… would fix both", "Until then" —
is exempt, which is what the prose actually means). It folds hard-wrapped
paragraphs into sentences before matching, because both a route
(`/platform/users/{id}/stations/`⏎`{station_id}/reset-attempts`) and its absence
cue regularly straddle a line break; the first, line-scoped version of the
checker produced five false accusations and that is why it reads sentences.
Clean as of 2026-09-23: **132 mentions agree.** It is deliberately *not* chained
into `npm run ci` — it reads a sibling repo's generated document, so a checkout
without `platform-api` would fail for the wrong reason. Regenerate
`openapi.json` before running it, or it will report the previous state.

What the checker cannot see is drift in the other direction and every claim not
written as a route, so read on.

`docs/port-gaps.md` and `docs/gap-closure-plan.md` were refreshed on 2026-09-23
and correctly record the ten fixed defects. The standing problem was
**understatement** — rows claiming absence where the code exists. The list of
such rows, and their status after the 2026-09-23 ledger pass:

- ~~`/api/v1/me` is read-only~~ — **corrected** (`PATCH` exists; the
  self-contradiction at `:76-79` reconciled).
- ~~"None of these four preference fields exist"~~ / ~~"the exam date has no
  field"~~ — **corrected**; `extra_reading_percent`, `exam_date`, `exam_code` are
  wired end to end, and the profile/preferences/exam rows now say so.
- ~~locked-read upgrade "not ported", checkout "unwired", `updated_at` "gone",
  "listed to everybody"~~ — the first is **corrected** (`LockedMediaGate.tsx`);
  the other three were re-checked and are **actually true** (`updated_at` is
  genuinely absent from `MediaRead`, `GET /media` really does list everything to
  everybody) so they were kept, not deleted — the drift was that the same row
  bundled a false half with a true one.
- ~~the four community rows~~ — **corrected** (`author_name`,
  `questions/{id}`, `?mine`, `replies?author=me`, all served and wired).
- ~~"Achievements has no route"~~ — **corrected** (`app/app/[workspace]/achievements/page.tsx`
  exists and renders it).
- ~~`gap-closure-plan.md` B4/B5 schedule served work as future~~ — **corrected**;
  B4–B9 now strike through every served item and list only what is genuinely
  open. Also corrected in the same pass, beyond this list: platform user-detail,
  org member/audit reads, reset-password, revoke/restore, moderation queue,
  audit actor/action filter, contract dates, at-risk list, platform-admin list,
  reading brief in the runner, station flags, `expected_revision`,
  `ready_to_run`, the Mocks tabs, the group/cohort/trainee edit table, bulk staff
  import, and the session delete/edit rows.

Re-run `npm run check:ledger` (currently **135 mentions agree**) after any
backend change and before trusting a row. Both docs live in
`platform-web/docs/`; there is **no** root-level `docs/gap-closure-plan.md`.

---

## 7. Not gaps — do not re-report these

confetti-check (dev scratch) · the four separate B2B console logins (one sign-in
now, by design) · tenant hard-delete (suspend is the mechanism) · browser-side
temp passwords · the LiveKit timer data channel (the server owns the clock) ·
trainee pre-join phase machine (`can_join` replaced it) · marketplace leaderboard
(already commented out in legacy) · `@stripe/stripe-js` (checkout is
redirect-based) · worker/webhook paths that are correctly uncalled from a browser
(`/assistant-sessions/*`, `/attempts/{id}/transcript-chunks`,
`/livekit-cloud-slot/*`, `/sessions/{id}/complete`, `/billing/webhooks/stripe`) ·
feedback-templates URLs, deliberately merged into rubric versions.

---

## 8. Set B — 2026-09-24: supervisor live session, and four investigate-only items

One half of a two-way split of a fresh code-verified audit (four parallel
read-only agents, source read directly, not this file). Set A (achievements
nav, SSO config screen, `searchUsers()` cleanup) ran in parallel, confined to
`capabilities/{account,platform}`, `domains/{train,platform}`,
`surfaces/*/surface.ts` — no file overlap with this section's work in
`domains/assess/**` and backend `sittings`/`catalog`/`roster`/`rubrics`.

### Task 1 — done: D1 (supervisor training-mode video)

`observer_token` (`sittings/service_join.py`) now grants `can_publish` when
the circuit's sitting is `mode == "training"`, looked up by a new
`repository_run.sitting_mode_for_circuit`. Exam mode is unchanged — still
unconditionally `can_publish=False`, with a test
(`test_an_examiner_can_listen_and_cannot_be_heard`) still green, plus a new
`test_a_training_supervisor_may_demonstrate_on_camera`. `RoomGrant` grew a
`can_publish: bool` field (both `sittings/schemas.py` and the hand-written
`foundation/livekit/types.ts`) so the browser knows before it tries, rather
than discovering a publish failure.

`ObserverPanel.tsx` renders the new `ObserverVideoGrid` (a supervisor's own
camera/mic toggle plus a tile per participant, reusing the same
`useTracks`/`VideoTrack` pattern `PeerVideoPanel.tsx` already uses for peer
practice) when `can_publish` is true, and falls back to the existing
text-only `Occupants` list otherwise — which is what an exam circuit still
gets. The candidate side is unaffected: the consultation screen was already
audio-only by design in both the retiring client and this one, so this is
"the supervisor may now be seen and heard," not a symmetric video call.

A live rubric-marking sidebar was scoped down from what was first proposed.
The engine has nothing to score until a station's consultation ends —
`readResults(attemptId)` is empty mid-station — so a sidebar cannot be filled
in *during* a consultation the way the legacy `CompactStructureRubric` could
(that rubric was independent of machine scoring; nothing in this backend
exposes one). What shipped instead, `LiveMarkingSidebar.tsx`, mounted on
`CircuitRunner.tsx`: reuses `SlotReview` (no new backend route, no
duplicated logic) against whichever of the circuit's *finished* slots the
supervisor picks, so marking station 1 no longer means leaving the live view
while station 2 is already running. A rubric fillable independent of machine
scoring, against a station's `marking_layout`, is real further work and
stays explicitly out of scope — it is a new form bound to a schema this
backend has (`rubrics/reads.py:validate_marking_layout`) but nothing today
reads for live use.

Verified: `backend/platform-api` — `make ci` on the `sittings` slice (lint,
mypy, the two new/changed tests, `4614 tests` in `tests/http`+`tests/guards`
overall); `make openapi` → `npm run platform:types` run centrally.
`platform-web` — `npm run ci` green (types, lint, `274/274` tests,
`check:ledger` 140 mentions agree). The pre-existing `docs/DATA-MODEL.md`
referrals drift reported by `make arch` predates this work (uncommitted
referral-payouts changes elsewhere in the tree) and is not this task's to fix.

### Task 3 — investigate-only findings (re-verified in source, not built)

1. **Exam catalog seed import — very likely a non-gap, same reasoning as the
   already-closed "library import" item above.** `GET /orgs/{org_slug}/exams`
   (`catalog/router.py:116-119`) already returns "this institution's own
   exams, plus the platform catalogue" in one list, and `POST
   /orgs/{org_slug}/programmes` (`:196-207`) resolves an `exam_code` against
   either scope directly — an institution adopts a platform exam by code,
   with no copy step, the same way a library station is adopted by
   reference rather than imported. A seed-catalog *picker* UI (legacy's
   `b2bListSeedCatalog`) would only be a discoverability convenience over
   what already works, not a missing capability. Recommend: confirm with the
   product owner and close as parity rather than build.
2. **Exam hard delete — a deliberate, consistent redesign, not a gap.**
   `catalog/router.py` has create/patch/publish/retire and no `DELETE`
   anywhere for exams, matching the same retire-not-delete pattern already
   confirmed elsewhere (tenant suspend, D8's practice-set refusal, D9's
   group/cohort refusal) — each because something else references the row
   and an unconditional delete would corrupt a defensible record (here, past
   sittings and results against the exam). Recommend: confirm and close, no
   build.
3. **Standalone feedback-templates backend is dead further down than
   previously recorded.** §7 above already notes the *frontend* URLs
   redirect into rubrics. Re-verified now: the backend service layer behind
   the router is equally uncalled — `grep`ing the whole `app/` tree for
   `published_feedback_template`/`service_feedback_binding` outside their
   own file returns nothing, so `router_feedback.py` (7 routes),
   `service_feedback.py` and `service_feedback_binding.py` form a complete,
   self-contained dead stack: nothing produces or reads a
   `FeedbackTemplateVersion` from any live flow. This matches D3's own
   finding that a sitting's rubric comes via its programme, not a bound
   feedback template. Recommend: delete the three files (router, service,
   binding) and their models/repository functions in one PR, verified by
   `make arch`/`make ci` staying green and `check_data_model.py` catching
   any orphaned table. Do not do this without a product sign-off — it is a
   deletion, not a fix, even though nothing currently depends on it.
4. **Trainee bulk-delete — consistent with the revoke/restore redesign, but
   flag the GDPR angle explicitly.** No route either side (`roster/router.py`
   has no `DELETE`; `domains/assess/roster/api.ts` has no delete call) —
   matches legacy's `bulk-delete` being replaced by access revoke
   everywhere else in roster. The one thing this recommendation adds beyond
   "confirm and close": revoke is not erasure. If this product has any
   GDPR/right-to-erasure obligation for trainee PII, that needs its own
   answer (a genuine hard-delete path, scoped narrowly, probably audited
   like the console's `delete-progress`) independent of whether the
   *product* wants bulk delete back as a convenience feature. Recommend:
   route this one to whoever owns compliance, not just product.

### All four built, 2026-09-24 — the owner asked for it, so they were built

Each was going to stay a proposal pending sign-off; the product owner asked to
implement all four instead, so this is what shipped, safety-first.

1. **Exam catalog seed import — confirmed a non-gap, nothing built.**
   `capabilities/authoring/sections/ProgrammesSection.tsx`'s "Add programme"
   dialog already lists every exam `listExams` returns — the institution's
   own plus the platform catalogue, merged the same way library stations
   are — and adopts one by code via `addProgramme`. That *is* the picker
   legacy's `b2bListSeedCatalog` offered; it was never missing, just not
   under a "seed catalogue" label.
2. **Exam hard delete — built.** `DELETE /orgs/{org_slug}/exams/{exam_id}`
   (`catalog/router.py`, `service_authoring.delete_exam`). Org-owned exams
   only; the platform catalogue keeps retire-only. `catalog` sits near the
   bottom of the `import-linter` layer contract — almost every other slice
   imports it, not the reverse — so it cannot pre-check every table that
   might reference an exam the way `station_sets` checks its one known
   `attempts` reference. The database's own `RESTRICT` constraints are the
   check instead: the delete is attempted, and an `IntegrityError` is caught
   and mapped to a clean `exam_in_use` (409), never a raw 500. Three tests
   in `tests/http/test_org_authored_exams.py`: an untouched draft deletes
   clean, one with a station on it is refused, a platform exam answers the
   same `unknown_exam` a stranger's id would. Frontend: a Delete action on
   `ExamsSection.tsx` with a `ConfirmModal`, hidden for platform exams the
   way Edit already was.
3. **Standalone feedback-templates — deleted outright**, not just
   flagged. Confirmed the whole stack was unreachable, one layer deeper
   than first recorded: `router_feedback.py` was never even mounted in
   `main.py` (0 hits in `openapi.json`, not merely uncalled from the
   frontend), and `attempts.feedback_template_version_id` — a column
   threaded through `repository.create_attempt`/`service.restart_for_slot`
   — was never once called with a real value anywhere in the codebase, nor
   ever read back. Removed: `router_feedback.py`, `service_feedback.py`,
   `service_feedback_binding.py`, `repository_feedback.py`, the
   `FeedbackTemplate`/`FeedbackTemplateVersion` models, their schemas and
   errors, the column and FK on `attempts`, and the two DB tables
   (migration `45481a44b73d`, tested both directions). `docs/DATA-MODEL.md`
   updated (69 → 67 tables) as the same change, per its own guard.
4. **Trainee bulk-delete — built, after fixing a real bug it depended
   on.** `candidate_result_revisions.trainee_id` was `ondelete="CASCADE"` —
   nothing had ever exercised the path, but a trainee delete would have
   taken their whole decision history with them silently, which is exactly
   the risk this item's own write-up flagged. Changed to `RESTRICT`
   (migration `11c001fd63a2`) to match every other outcome table in this
   schema, *then* `DELETE /orgs/{org_slug}/trainees/{trainee_id}` was built
   on top of it (`roster/service_edit.delete_trainee`), same
   catch-the-`IntegrityError` pattern as #2 above — `roster` sits below
   `results` in the layer contract and has the same inability to pre-check.
   Group and cohort membership still cascade away, because that is the
   trainee's own bookkeeping, not a record about them. Two tests in
   `tests/http/test_roster_edit_routes.py`. Frontend: a Delete button in
   `TraineeRowActions.tsx`, wired through `TraineesPanel.tsx`'s existing
   confirm-dialog machinery, with a `trainee_in_use` catch that tells the
   admin to revoke instead of just surfacing the raw error.
   **The GDPR-erasure question from the original write-up is still open**
   — this is bulk delete as a product convenience for an unexamined roster
   row, not an erasure path for someone with a real decision on record.
   That still needs a compliance answer.

Verified together: `backend/platform-api` — the full targeted suite across
every touched slice (`catalog`, `roster`, `results`, `sittings`, `rubrics`,
`attempts`) plus `tests/unit`, `tests/guards`, `tests/repository` (which
includes the schema-drift check against the two migrations) — **5539
passed**; `ruff`/`mypy` clean on every touched slice;
`check_data_model.py` clean for this change (a separate, pre-existing
`referrals` drift from unrelated in-flight work is not this change's).
`platform-web` — `npm run ci` green: types, lint, **274/274** tests,
`check:ledger` **141 mentions agree**. `make openapi` →
`npm run platform:types` regenerated centrally after both migrations.
