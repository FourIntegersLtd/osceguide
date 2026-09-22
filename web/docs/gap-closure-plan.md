# Gap closure plan

The plan for closing everything in `port-gaps.md`, plus the UI-parity sweep.
Written 2026-09-20 after a deep review of `frontend/` against `platform-web/`
and a read of the full gap register, `port-plan.md` (J16, B1–B3) and recent
`platform-api` history.

Standing acceptance rule for all of it: **a ported screen, modal, button or
flow must be an exact match of the legacy UI wherever the legacy screen
exists.** The old screen is the specification; the implementation may be
rewritten, the pixels may not.

---

## Phase 0 — Security first — **in progress**

Blocks everything else. All three are backend (`platform-api`) fixes.

| # | Item | Fix |
|---|---|---|
| S1 | `GET /orgs/{slug}/stations` hands a trainee the whole station document — `StationRead.content` carries the patient brief, persona and examiner notes, and `OrgReader` admits trainees. Anybody on a roster can read the material for stations they are about to be examined on. | Reader-scoped projection: a caller who is a trainee (not admin/staff) receives only the candidate-facing content, or a dedicated brief read a candidate may call. The client-side workaround (`SelfPractice.readingBrief()`) stays but stops being load-bearing. |
| S2 | The circuit runner shows no reading brief during reading time (same root cause as S1). | Solved by S1's candidate-scoped read; the runner wires it (or `GET /attempts/{id}/brief` where an attempt already exists). |
| S3 | `POST /stations/{id}/comments` with a nonexistent station id answers `internal_error` instead of `station_not_found`. | Map the FK failure in the service. |

## Phase 1 — Wire what the backend already serves — **in progress**

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

**B4 · Identity & account** — `PATCH /me` (name); a `preferences` object and
write (AI consent, extra reading time, colleague-waiting email, Athena
onboarding replay); soft account deletion.

**B5 · Community & media** — `author_name` on `PostRead` (most visible gap in
the register); `GET /community/questions/{id}`; `GET /community/replies?
author=me`; `mine` filter on the feed; `q` + `exam_code` on `GET /media`;
specialty/tag column; `updated_at`; `total_count`; search excerpts; media
asset upload (pairs with the object-store decision).

**B6 · Mocks & attempts** — `PATCH`/`DELETE /me/station-sets/{id}`;
`GET /attempts/{id}/debrief` + `POST /attempts/{id}/debriefs` (library
debrief, examiner read, cheaper debrief page); a `coverage` event on
`GET /attempts/{id}/stream` (restore LiveCoveragePanel/Feed); persist station
flags; widen attempt result/transcript visibility to org members (GP lead).

**B7 · Roster & team** — email join on `GET /memberships`;
`POST /memberships/{id}/resend-invite`; `PATCH`/`DELETE` trainee-groups and
cohorts; `PATCH /trainees/{id}`; `GET /trainee-groups/{id}/members`;
`POST /memberships/bulk`.

**B8 · Results, reviews & circuits** — `GET /me/sittings/{id}/circuit-review`
(largest thing J14 could not port); finalize-state read on circuit review;
`GET .../slots/{id}/reviews/mine`; `revision` on `SaveDecision`; bulk release
+ notify candidates; cohort export.

**B9 · Authoring & platform console** — platform-scope brief `PATCH` +
version `DELETE`; `GET .../stations/{id}` and `.../versions`; `q`/exam
filters; `cursor` on template listings; station-usage count; library-import
copy endpoint; contract dates + parent on `OrganizationRead`;
`is_platform_admin` on `UserSummary`; directory search params; moderation
queue endpoint everywhere; audit actor/action filters; referral per-referee
history + admin console under `/staff`.

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
