# Gap closure plan

The plan for closing everything in `port-gaps.md`, plus the UI-parity sweep.
Written 2026-09-20 after a deep review of `frontend/` against `platform-web/`
and a read of the full gap register, `port-plan.md` (J16, B1–B3) and recent
`platform-api` history.

**Status 2026-09-23: Phases 0 and 1 are closed and verified** (backend
`f5dd9d6`/`155032f`, web `061fe44`, plus the feedback-counter and reading-brief
follow-ups; full suite 6,057 passed / 3 known-local-artifact failures; web CI
216/216). The five decisions from the closure round (S2 hardening, lint
cleanup, backend breakage, countdown parity, feedback counter) all went yes —
see Q1–Q5 below. Phase 2 (parity sweep) and Phases 3–4 are open.

**Later on 2026-09-23.** A screen-by-screen audit of `frontend/` against
`platform-web/` — rather than a read of this plan — found ten things that are
*broken* rather than merely unported, and fixed them: the examiner's marking
screen received no attempt so scored nothing, the retiring client's session URLs
redirected to a name the route tree had changed, join links and the four console
sign-ins landed on pages that do not exist, `must_change_password` was never
enforced, the partner arm could not invite an editor, `PUT /circuits/{id}` had no
caller, partner attribution recorded no arrivals and spent no signups, analytics
and consent and `robots.txt`/`sitemap.xml` had no new home, and `platform-web`
still imported `frontend/src/b2b` and `frontend/src/shared` through a build
alias — so it could not outlive the tree it replaces. Each row, with evidence and
the fix, is in `port-gaps.md` under "2026-09-23 — a full re-check". Web CI is
222/222 with those included, and `npm run build` no longer needs `frontend/` at
all. The lesson for this file: it describes a plan, not the tree — re-verify in
code before scheduling work from a row here.

Standing acceptance rule for all of it: **a ported screen, modal, button or
flow must be an exact match of the legacy UI wherever the legacy screen
exists.** The old screen is the specification; the implementation may be
rewritten, the pixels may not.

---

## Phase 0 — Security first — **done**

Blocks everything else. All three are backend (`platform-api`) fixes.

| # | Item | Fix |
|---|---|---|
| S1 | `GET /orgs/{slug}/stations` hands a trainee the whole station document — `StationRead.content` carries the patient brief, persona and examiner notes, and `OrgReader` admits trainees. Anybody on a roster can read the material for stations they are about to be examined on. | Reader-scoped projection: a caller who is a trainee (not admin/staff) receives only the candidate-facing content, or a dedicated brief read a candidate may call. The client-side workaround (`SelfPractice.readingBrief()`) stays but stops being load-bearing. |
| S2 | The circuit runner shows no reading brief during reading time (same root cause as S1). | Solved by S1's candidate-scoped read; the runner wires it (or `GET /attempts/{id}/brief` where an attempt already exists). |
| S3 | `POST /stations/{id}/comments` with a nonexistent station id answers `internal_error` instead of `station_not_found`. | Map the FK failure in the service. |

## Phase 1 — Wire what the backend already serves — **done**

Frontend-only. These endpoints landed (platform-api c04411e, b1c597d,
ff2450c) and nothing calls them yet.

1. **Checkout return routes** — `src/app/billing/complete/page.tsx` and
   `src/app/pricing/page.tsx`. The backend hardcodes these URLs in
   `billing/service_checkout.py`; without the route files a paying customer
   lands on a 404. Highest urgency in this phase.
2. `fetchLandingStats()` → `GET /site/statistics` (cached, carries `as_of`).
3. `landingBlogs.ts` → public `GET /media` / `GET /media/{slug}` (the
   landing's blog rail comes back).
4. Messages / contact form → `POST /site/messages`; the "Help Us Improve"
   section goes back into `landingSections`. The screen is a port — match the
   legacy `/messages` UI exactly.
5. Exam-date countdown + `ExamWishes` → `users.exam_date` on `/me`.
6. Extra reading time → `users.extra_reading_percent`, applied at attempt
   creation to a person's own practice (not to circuit clocks).
7. SSO discovery on the sign-in page → `GET /auth/sso/sign-in?host=…`;
   hide the password form on `sso_only` (display rule only — a password login
   is not refused until the sign-in decision, S-1, is made).
8. **Bug:** `domains/train/Access.tsx` reads `GET /me/receipts` (a
   `Page[str]` of receipt ids) as if items were objects — every field renders
   `undefined`, blank rows for every paying user. Follow
   `capabilities/account/api.ts#listReceipts`: list ids, then read each.
   Receipt date/money fields are preformatted display strings — print
   verbatim, never re-parse or reformat.
9. Attempt history — `GET /me/attempts` is served: wire the mock station
   table's "All previous Transcripts/Feedbacks" links and restore "Review
   Last Attempt" beside "Talk Through Last Attempt".
10. Station-comment dedupe — delete the rebuilt panel in
    `capabilities/stations`, import the real one from
    `@/capabilities/community`.

## Phase 2 — UI parity sweep

The port plan already mandates parity (rules 1, 2 and 7); the mismatches are
an enforcement failure. Plan:

1. Parity harness: legacy `frontend/` on :3000, `platform-web` on :3100, same
   seeded account.
2. Screen-by-screen walkthrough — train arm first, then assess, platform,
   partner. Compare layout, components, copy, buttons, modals, empty/loading/
   error states, fonts and tokens.
3. Record every divergence in `docs/ui-parity.md`: legacy file → platform-web
   file → what differs → fix.
4. Fix the divergences. Redesign is out of scope; arms with no legacy
   equivalent (hire) are exempt.
5. Regression guard: Playwright screenshot baselines for key screens.

## Phase 3 — Backend gap bundles (B4–B9)

Each bundle is one coherent platform-api PR (endpoint + tests + migration)
plus its platform-web wiring, closing the matching `port-gaps.md` rows
(annotate, don't delete).

**B4 · Identity & account** — ~~`PATCH /me` (name)~~ **served and wired**
(`ProfilePanel`); ~~extra reading time~~ **served and wired** (`PreferencesPanel`
writes `extra_reading_percent`). Still open: a `preferences` object for AI
training consent / colleague-waiting email / Athena onboarding replay; soft
account deletion.

**B5 · Community & media** — ~~`author_name` on `PostRead`~~,
~~`GET /community/questions/{id}`~~, ~~`GET /community/replies?author=me`~~,
~~`mine` filter on the feed~~ — **all four served and wired** (2026-09-23).
Still open: `q` + `exam_code` on `GET /media`; specialty/tag column;
`updated_at`; `total_count`; search excerpts; media asset upload (pairs with the
object-store decision).

**B6 · Mocks & attempts** — ~~persist station flags~~ **done 2026-09-23** (the
`station_flags` table, `/me/station-flags`, `/platform/station-flags`, the
consumer "Flagged Stations" tab and the `/staff/station-flags` queue).
~~`PATCH`/`DELETE /me/station-sets/{id}`~~ **done 2026-09-23** —
`SessionCardActions` puts the pencil and bin on each card in `MockSessions`.
Still open: `GET /attempts/{id}/debrief` +
`POST /attempts/{id}/debriefs`; a `coverage` event on
`GET /attempts/{id}/stream`; widening attempt result/transcript visibility —
**the transcript/result half is done** (named circuit supervisor now reads
them, and `AttemptTranscript.tsx` on the examiner's `SlotReview` screen is the
caller); the GP-lead-across-org half is a decision, not a gap.

**B7 · Roster & team** — the invitation re-send (`POST /api/v1/orgs/{org_slug}/trainees/{trainee_id}/resend-invitation`),
trainee-group and cohort `PATCH`/`DELETE`, `PATCH /api/v1/orgs/{org_slug}/trainees/{trainee_id}`,
and `POST /api/v1/orgs/{org_slug}/memberships/bulk` — **served and wired
2026-09-23**: `TraineeEditDialog`, `TraineeRowActions` (resend),
`GroupEditDialogs`, `CohortsPanel` + `CohortEditDialogs`, and `BulkInviteDialog`
with `team/csv.ts`. Still open: email join on `GET
/api/v1/orgs/{org_slug}/memberships`; a `GET …/trainee-groups/{group_id}/members`
(the path is `PUT`-only today, so the group editor still resolves membership
through `POST /roster/resolve`).

**B8 · Results, reviews & circuits** — ~~`revision` on `SaveDecision`~~
**done 2026-09-23** (`expected_revision` + `decision_revised` 409). ~~bulk
release + notify candidates~~ — **done, but read it correctly:** there is no
bulk *endpoint*. `Results.tsx` fans the per-candidate
`POST …/decision/release` out over the signed-off rows and reports each
candidate's refusal individually, and the release itself enqueues the
notification unconditionally (`results/service.py`). A server route would be a
different, transactional thing and nobody has asked for one. Still open:
`GET /me/sittings/{id}/circuit-review`;
finalize-state read on circuit review; `GET .../slots/{id}/reviews/mine`;
~~cohort export~~ **served and wired** (`GET …/sittings/{id}/readout`,
exported by `results/ReadoutExport.tsx`).

**B9 · Authoring & platform console** — ~~`GET .../stations/{id}` and
`.../versions`~~, ~~`q`/exam filters~~ (`?search=` on the library), ~~contract
dates + parent on `OrganizationRead`~~ (contract dates served; `parent` still
absent), ~~`is_platform_admin` on `UserSummary`~~, ~~audit actor/action filters~~
(`GET /platform/audit` takes `actor_email`/`action`/`org_slug`), ~~moderation
queue endpoint everywhere~~ (`/platform/moderation/posts` served and mounted at
`/staff/moderation`) — **served 2026-09-23**. Still open: platform-scope brief
`PATCH` + version `DELETE` (product decision D4); `cursor` on template listings;
station-usage count; ~~library-import copy endpoint~~ (**not a gap** — the
retiring modal never copied: `StationDetailPanel` has no write, and an org
already adopts by reference through `visible_to` plus the library picker inside
`CircuitBuilder`); directory search
params; referral per-referee history + admin console under `/staff`.

## Phase 4 — Product decisions (unblock in parallel)

Parked in platform-api `docs/OPEN-QUESTIONS.md`; each needs a decision before
code:

1. Achievements/streaks (S-3) — what is a streak when attempts are the only
   progress record?
2. Photo upload / media assets — which object store (S3 already used by
   media_production)?
3. SSO sign-in (S-1) — who verifies identity? Legacy brokered
   Clerk→Microsoft; neither backend has a flow to port.
4. Push notifications — adopt `web-push`?
5. Peer practice — recording/transcript/AI feedback (P-1), decline/requeue
   protocol, optional rating + `would_practice_again` persistence,
   per-participant feedback columns.
6. Referral payouts — bank-details storage + payout flow, or drop?
7. Practice mocks on the Assess arm — mount `/me/station-sets` there?
8. Ortho CV upload — keep or drop?
9. Tenant delete — confirmed dropped; suspension is the mechanism.

## Sequencing

```
Week 1:    Phase 0 + Phase 1; parity harness + train-arm walkthrough starts
Weeks 2-3: Phase 2 fixes + B5, B6 (most user-visible)
Weeks 3-4: B4, B7, B8
Week 5+:   B9; Phase 4 items as decisions land
```

## Definition of done (every item)

- Backend: endpoint + tests + migration where needed; `poetry run pytest -q`
  green; the route added to `scripts/smoke.mjs`.
- Frontend: wired through an `api.ts` (no network calls elsewhere), no
  literal route prefixes, strict types; `npm run ci` green.
- Parity: the screen verified side by side with the legacy app where a legacy
  screen exists.
- `port-gaps.md` row annotated as served (the file's own convention: entries
  stand with a note rather than being deleted).
