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
   — red at clean `HEAD`. Passes alone; the engine tests above it import the real
   `osce_assessment`, which pulls `openai`, and the assertion reads
   `sys.modules`. Order artifact.
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

Current real state: platform-web `types` 0 errors, `lint` 0 errors / 72 warnings,
**227/227 tests**. Backend `lint`, `typecheck`, `arch`, `guards` (4405) clean;
6072 tests pass with only the three artifacts above.

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
| D1 | Supervisor mic/camera + video grid. `observer-token` is minted `can_publish=False` unconditionally (`sittings/service_join.py:76-101`); `voice/README.md:42-45` calls it "a guarantee, not a UI state" | reverse **for training mode only** — a supervisor who cannot demonstrate in a training circuit is a real loss; keep exam mode subscribe-only |
| D2 | Trainee result narrowing — `MyResult.tsx:10-19` says the omission is disclosure policy | keep, but add score-vs-threshold where the outcome is already released |
| D3 | Per-sitting feedback-template choice — `NewSitting.tsx:142-143`: rubric comes via programme | keep; record as a decision, not a gap |
| D4 | Platform-scope authoring has no brief PATCH / draft DELETE / programmes — `capabilities/authoring/api/scope.ts:41-42` | keep unless staff actually author briefs |
| D5 | Feature-request admin retired — `legacyRedirects.ts:226` sends `/features/**` to `/` as "superseded" | confirm retired |
| D6 | No PWA. **Verified fact:** `frontend/public/manifest.json` never existed and `frontend/public/sw.js` is 38 lines of `console.log` with every push handler commented out. There was nothing to port | confirmed; `app/metadata.ts:10-21` documents it |

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

## 4. Phase 2 — Integrity fixes (~3 days). NEXT

Three places where the product currently misrepresents its own state.

**2.1 Station flags are a lie.** `POST /me/station-flags` is
`_ = principal; _ = body` at `backend/platform-api/app/features/identity/router.py:237-240`,
docstring "Persistence is TODO". The button in
`capabilities/station-runner/StationChrome.tsx:60-66,97-108` confirms a report
that is discarded. There is **no `StationFlag` model anywhere.** Needed: model +
migration, persist, `GET /platform/station-flags` + resolve, staff browse screen.
`domains/train/mocks/Mocks.tsx:28-30` already says "Both mount themselves when
those land."

**2.2 No revision control on decisions.** `SaveDecision`
(`app/features/results/schemas.py:20-27`) has no revision field, though storage is
append-only with workflow guards (`results/repository.py:48-81`) and the UI shows
`Revision N` (`results/CandidateDecision.tsx:149`). Concurrent draft saves are
last-writer-wins. Legacy sent `expectedRevision`. Needed: `expected_revision`,
409 on mismatch, send it from the UI.

**2.3 `ready_to_run` counts only authored stations.**
`dashboard/service_org.py:49-58` gates on `counts.stations > 0` and `count_for_org`
filters `owned_by(Station, org_id)` (`stations/repository.py:212-214`). A
catalogue-only institution with a markable programme is told to keep setting up
while already running exams. Frontend already defers to the backend
(`OrgDashboard.tsx:66,127-136`), so this is a predicate change plus a rename.

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

**Phase 5, docs.** See §6. Plus two verification holes: there is **no browser
parity harness** (no Playwright; `scripts/smoke.mjs` needs a live platform-api),
so "exact visual/UX match with legacy" — the stated acceptance rule — is
unmeasured; and nobody has ever run `npm run build` with `frontend/` absent, so
self-containment is proven statically (no aliases, no escaping imports, no
`prebuild`) but never demonstrated. Do the latter in CI on a checkout that omits
`frontend/`, not by deleting it locally.

---

## 6. The ledger drifts in one direction

`docs/port-gaps.md` (~1143 lines) and `docs/gap-closure-plan.md` were both
refreshed on 2026-09-23 and now correctly record the ten fixed defects. What is
still wrong is **understatement** — rows that claim absence where the code exists.
Every §5 item you land must delete or correct its row, and these already-known
stale rows should go in the same pass:

- `port-gaps.md:381` "`/api/v1/me` is read-only" — false, `PATCH` exists
  (`identity/router_me.py:26`); the same file contradicts itself at `:76-79`
- `:383` "None of these four fields exist on `platform-api`" — false,
  `extra_reading_percent` is wired end to end
- `:385` "The exam date has no field" — false (`schemas.py:57` ←
  `ExamDateControl.tsx:99`)
- `~:139-143` locked-read upgrade "not ported", checkout "unwired", `updated_at`
  "gone", "listed to everybody" — all false (`LockedMediaGate.tsx`,
  `ArticleView.tsx:29-30`, `filterMediaByExam`); `:392` already says checkout is
  wired
- `~:160-163` the four community rows — all now implemented
- `:89` and route table `:416` "Achievements has no route" — the file exists
- `gap-closure-plan.md` B4/B5 still schedule `PATCH /me (name)`, `author_name`,
  `GET /community/questions/{id}` and the `mine` filter as *future* work

Both docs live in `platform-web/docs/`; there is **no** root-level
`docs/gap-closure-plan.md`.

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
