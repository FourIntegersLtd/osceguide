# Core journeys

The journeys a real person must be able to finish. Each is driven in a real
browser by a Playwright spec under `web/e2e/`, against a local platform-api.
Gap IDs refer to `docs/EXPERIENCE-GAPS.md`.

"Local" means it runs with no LiveKit voice. Where a step needs a spoken room,
the journey drives the api seam instead, or the step is listed as skipped with
the reason. The seams used are:

- **circuit start and end** through the api: start works without LiveKit;
  "Next station" returns `503 voice_unavailable`; ending the circuit closes the
  slot as skipped.
- **database seam** (`web/e2e/support/db.ts`): the rows a finished marking
  leaves behind (an evaluated attempt and its `assessment_results`), because
  marking needs a spoken transcript. Only runs after the local-api assertion.
- **microphone**: headless Chrome's `getUserMedia` never resolves, so nothing
  that waits on the mic check can be reached.

## How to run

Prerequisites: docker postgres up, `poetry run alembic upgrade head`,
`poetry run python scripts/seed_platform.py`,
`poetry run python scripts/seed_station_templates.py --apply` (needs a platform admin), and platform-api on `:8002`
(`make start` in `api/`). Then, from `web/`:

```bash
export PATH="$HOME/.nvm/versions/node/v22.22.3/bin:$PATH"
npm run e2e           # everything
npm run e2e:train     # consumer journeys
npm run e2e:assess    # institution journeys
```

Playwright starts its own Next dev server on `:3101` (separate `distDir`,
`.next-e2e`) with `/api/v1` proxied to `http://127.0.0.1:8002`. Set
`E2E_REUSE_SERVER=1` to reuse one that is already running. Global setup refuses
to write anything unless the api host is localhost, then creates a fresh
organisation `e2e-<id>` with an admin, supervisor, trainee, a consumer and a
newcomer, so a run never depends on earlier data. Override with
`E2E_API_URL`, `E2E_WEB_URL`, `E2E_PG_CONTAINER`. Sign-in is rate limited to
10 a minute; the helpers wait and retry on 429 (`loginPatiently` is a test-only workaround for that limit, not product behaviour). Failures keep a trace and
screenshot in `web/test-results/`.

## TRAIN: the consumer

| ID | Journey | Local | Spec |
|---|---|---|---|
| TRAIN-1 | Sign in, reload, sign out | yes | `train/sign-in.spec.ts` |
| TRAIN-2 | Register, choose an exam, reach the first station | yes | `train/first-visit.spec.ts` |
| TRAIN-3 | Create a practice session, reach the pre-start screen | yes, to the pre-start screen | `train/practice-session.spec.ts` |
| TRAIN-4 | Read feedback on a marked station; dashboard moves | yes, marked row seeded | `train/feedback.spec.ts` |
| TRAIN-5 | Update profile, see plans | yes | `train/settings.spec.ts` |
| TRAIN-6 | Speak a practice station and be marked | no, needs LiveKit | skipped |
| TRAIN-7 | Help is on every learner screen (phone: floating button; desktop: toolbar, no Inbox icon) | yes | `train/help-everywhere.spec.ts` |
| TRAIN-8 | On a phone (390px, touch) every screen scrolls to its end and nothing scrolls sideways: the station room, the peer room, every learner, institution and staff page | yes | `train/phone-layout.spec.ts` |
| TRAIN-12 | Signed up for one exam, holds another, the browser remembers the sign-up exam under the retired switcher's key (guards the deleted reader only; the null-exam rule is `examCode.test.ts`): the marketplace lists and claims the held exam's slot, no `not_entitled` | yes | `train/marketplace-exam.spec.ts` |
| TRAIN-13 | The app does not know the learner's exam (the dashboard read fails with a 502, or the api names none): AI Practice (Setup and Combine tabs) and the marketplace explain it, offer "Try again", show no form, no actions, no progress bar and no free-trial paywall; the retry brings the real exam back | yes | `train/null-exam.spec.ts` |

**TRAIN-1.** Actor: a registered consumer.
1. Open `/login`, enter email and password, submit.
2. Land in the app signed in; reload the page.
3. Still signed in. Sign out; `/app` sends back to `/login`.

Outcome: a reload keeps the session, sign-out ends it (the refresh token is
revoked server-side). Gaps: A-1, A-3, A-6.

**TRAIN-2.** Actor: a brand-new visitor.
1. Open `/register`, create an account.
2. See the exam picker (`users.exam_code` is empty); choose SCA.
3. Reach the first-station prompt. 2b: before an exam is chosen, `/app/me/**`
   shows only the picker.

Outcome: a newcomer cannot reach a page that assumes an exam. Gaps: A-3, A-6.

**TRAIN-3.** Actor: a consumer with an exam.
1. Open practice, "New session"; the session name is generated ("Session 1").
2. Pick a station and open the pre-start screen.

Outcome: the session exists and the start screen opens. Gaps: T-2, C-2.
Not covered: pressing Start, which waits on the microphone check (see TRAIN-6).

**TRAIN-4.** Actor: a consumer with a marked attempt.
1. (Seam) a marked practice attempt is written for the user.
2. Open the feedback page for it; the domain rating and quoted phrase show.
3. Open the dashboard; the practised count has moved.

Outcome: feedback reads from the rubric, the dashboard reflects the attempt.
Gaps: C-1, T-12 (self practice has no feedback route yet).

**TRAIN-5.** Actor: a consumer.
1. Open settings, change the display name, save, reload; it persists.
2. Open plans; the plans render.

Outcome: profile edits persist. Gaps: A-6.

**TRAIN-6 (skipped).** Actor: a consumer. Steps: start a station, allow the
microphone, talk to the simulated patient, end, wait for marking, read
feedback. Skipped: needs LiveKit workers, and the mic check never resolves in
headless Chrome. Its pieces are covered by TRAIN-3 (set-up), TRAIN-4 (the
marked result) and `verify-attempt-engine` (the room itself). Gaps: T-7, C-1.

## ASSESS: the institution

The admin's menu, in order: **Home**; **Run** (Sittings, Now running, Results);
**Organise** (People, Exams); **Insight** (Reporting); **Settings**. A supervisor
sees Home, Sittings, Now running, Results, People (read only) and Reporting. A
trainee sees My training, Practice sessions and Self practice. Boards:
`docs/institution-overhaul/design/`. The Schedule a sitting wizard, the Sitting
page, the console and the live board are the overhaul's phase 3; the steps below
describe them from `ScheduleSitting.md` and `Sitting.md`, and the specs move to the
new labels when phase 3 merges.

| ID | Journey | Local | Spec |
|---|---|---|---|
| ASSESS-1 | Admin schedules a sitting with the Schedule a sitting wizard | yes | `assess/build-sitting.spec.ts` |
| ASSESS-2 | Trainee waits; supervisor starts; the brief opens | yes | `assess/run-circuit.spec.ts` |
| ASSESS-3 | No voice room: supervisor is told, can end the circuit | yes (is the seam) | `assess/run-circuit.spec.ts` |
| ASSESS-4 | Reviewer marks, admin decides and signs off, releases, candidate reads | yes, marked slot seeded | `assess/mark-and-release.spec.ts` |
| ASSESS-5 | Roles: supervisor, trainee and People boundaries | yes | `assess/roles.spec.ts` |
| ASSESS-6 | Candidate sits a station by voice | no, needs LiveKit | skipped |
| ASSESS-7 | Training room: supervisor and trainees in one room, live marking, peer marks, close | no, needs LiveKit; walked by hand (`verify-institution`, Training room) | none |

**ASSESS-1.** Actor: institution admin.
1. Open Home. Until setup is done it shows one step at a time ("Step N of 5",
   "Continue setup"); once it is done Home is "Today", with a "Schedule a sitting"
   button. (The e2e organisation is already set up, so the journey starts at the
   button.)
2. Open "Schedule a sitting". The six steps unlock in order and nothing is made
   until the last: Basics (name, an exam that is "Ready to schedule", kind,
   date, year group), Stations, Candidates (people, groups or year groups), Timing
   and breaks, Supervisor, Review and create.
3. "Create sitting" shows "N candidates x M stations" and makes the sitting and its
   circuits (a formal exam gets one circuit per candidate).
4. The Sitting page opens, with one primary button that follows the next step; the
   sitting is on Sittings with its circuits assigned.

Outcome: a sitting a supervisor can run. Gaps: B-3, B-5, B-7, B-39 (open: the list
cannot flag "Needs circuits"), B-40.

**ASSESS-2.** Actor: trainee, then supervisor.
1. The trainee opens their portal and sees the sitting is not started.
2. The supervisor opens the circuit console and starts it.
3. The brief opens for the trainee.

Outcome: start works and a second Start does not restart it. Gaps: R-2, R-3, S-1.

**ASSESS-3.** Actor: supervisor.
1. After Start, press "Next station".
2. With no voice room, the console shows an alert (voice unavailable).
3. End the circuit; confirm "End the circuit".

Outcome: the failure is stated, and the circuit can still be closed. Gaps: S-1,
S-2, S-7 (open: nothing advances a due circuit when the worker is down).

**ASSESS-4.** Actor: examiner and admin, then the candidate.
1. Circuit ended; (seam) the slot gets an evaluated exam-slot attempt.
2. Before release the candidate sees "Not released yet", and the api returns
   them nothing for the slot review.
3. The reviewer finds the slot (Results opens with "Needs your attention"; a
   supervisor also has "Stations to review" on Home), rates every domain Green and
   completes the review.
4. The admin opens the sitting's results, chooses Pass, writes a rationale, signs
   off (the row offers "Back to draft").
5. The admin presses "Release 1 signed-off result" and confirms.
6. The candidate's result page now shows the outcome.

Outcome: release is the only door to the candidate. Gaps: R-1, R-4, R-6.
Finding while building it: after "End the circuit" with no voice, the slot is
skipped and the sitting stays "0 of 1 stations marked" even after a human
review is completed, so no outcome can be decided without the seam.

**ASSESS-5.** Actors: supervisor, trainee, admin.
1. A supervisor sees Sittings but not "Schedule a sitting" (5), and their Home is the
   supervisor Home with "Stations to review".
2. A trainee lands on their own portal, not the console (5b).
3. The admin's People page (Trainees tab) lists the trainee and offers "Add people"
   (5c); a supervisor sees People read only and no "Add people".

Outcome: each role sees only what its capabilities grant. Gaps: B-5, R-2, R-6.

**ASSESS-6 (skipped).** Actor: candidate. Steps: join the room, speak to the
patient, the examiner agent closes, scoring runs. Skipped: LiveKit. Covered in
pieces by ASSESS-2/3 and ASSESS-4's seam. Gaps: S-1, S-2, R-5.

**ASSESS-7.** Actors: supervisor, two trainees on a training circuit.
1. The supervisor starts the circuit and joins the room; both trainees join with camera on.
   Only the trainee with the turn has a microphone; "Bring in <next>" moves it.
2. The supervisor ticks the scheme while the trainee speaks (saved as a draft review, notes
   untouched); the waiting trainee marks the same scheme and the supervisor sees those marks live.
3. The supervisor opens the floor so everyone may speak, then ends the circuit: the room stays.
4. The supervisor releases their review; the trainee whose turn it was reads "From the room".
5. "Close the room" disconnects everyone. A room nobody closes is closed after six hours.

Outcome: peer marks never feed the score; release of the supervisor's review is the only door
to the trainee. A live tick never undoes a released review (`review_already_completed`).

## HIRE: the employer

| ID | Journey | Local | Spec |
|---|---|---|---|
| HIRE-1 | Employer admin sees the hiring menu (Overview; Run: Assessments, Now running, Results; Organise: Candidates, Exams; Insight: Reporting), not the institution's wording | yes, `@staging` | `hire/employer.spec.ts` |
| HIRE-2 | A candidate is shown only "My assessments" | yes, `@staging` | `hire/employer.spec.ts` |

Actors: an `employer` organisation's `institution_admin`, and a `trainee`
member. The hire menu has the same sections as Assess, in hire words (Assessments,
Candidates, Assessors); Exams and Reporting are reachable. Outcome: the Hire arm renders Assess's screens in employer wording and a
candidate is never offered a staff read (403 for them). Gaps: B-5, R-2.

## PARTNER: the publishing partner

| ID | Journey | Local | Spec |
|---|---|---|---|
| PARTNER-1 | Partner admin opens Overview, Reporting and Team; no examining menu | yes, `@staging` | `partner/partner.spec.ts` |

Actor: a `partner_admin` of a `partner` organisation. Outcome: the three
partner screens open and the institution's Sittings and People never appear.

## CONSOLE: the staff console

| ID | Journey | Local | Spec |
|---|---|---|---|
| CONSOLE-1 | Platform admin opens `/staff`, Organisations and Users | yes, `@staging` | `console/staff-console.spec.ts` |
| CONSOLE-2 | A learner who opens `/staff/organizations` lands on `/app/me`, no staff menu | yes, `@staging` | `console/staff-console.spec.ts` |
| CONSOLE-3 | An institution admin who opens `/staff` lands on `/app/<org>`, no staff menu | yes, `@staging` | `console/staff-console.spec.ts` |
| CONSOLE-4 | Platform admin signs out of `/staff/users`; an institution admin signs in on the same tab and lands on `/app/<org>` | yes, `@staging` | `console/staff-console.spec.ts` |

## ROLES: the role matrix

`roles/role-matrix.spec.ts` (ROLES-1) signs in as each seeded role (institution
admin, supervisor, trainee, consumer, employer admin, employer candidate,
partner admin, platform admin), reads the links in the sidebar it is shown,
opens each, and fails on any 401/403/404 from the page's own api calls or a
"Page not found" heading.

## SWITCH: one tab, more than one person

| ID | Journey | Local | Spec |
|---|---|---|---|
| SWITCH-1 | A learner on `/app/me` signs out; an institution admin signs in on that tab and lands on `/app/<org>` | yes | `roles/switch-account.spec.ts` |
| SWITCH-2 | A session ends on `/app/<org>/sittings`: the same admin signs back in to it, a learner signing in instead lands on `/app/me` | yes | `roles/switch-account.spec.ts` |
| SWITCH-3 | Deleting an account ends on `/login?deleted=1` with its notice | yes | `roles/switch-account.spec.ts` |

## Running in CI and against staging

- **ci-web.yml, job `journeys`**: Postgres service, `alembic upgrade head`,
  `seed_platform.py`, `bootstrap_admin.py` (the platform admin, TOTP from
  `ADMIN_TOTP_SECRET`), `seed_station_templates.py --apply` (publishes as that admin), uvicorn on :8002, `next build` with
  `PLATFORM_API_URL` pointing at it, then `npm run e2e` with `E2E_PREBUILT=1`
  and `E2E_DATABASE_URL` (the database seam uses `psql` there, not docker).
  Global setup authors three minimal published SCA stations on the SCA template
  when the library is empty, and puts an SCA plan on sale (a placeholder Stripe
  price) when none is. Never a remote api.
- **Staging** (`promote-web.yml` job `staging-journeys`, `promote-api.yml` before
  gate 5): `web/scripts/smoke.mjs`, then `E2E_TARGET=staging npx playwright
  test`, which runs only specs tagged `@staging` (read-only; they create
  nothing). Both skip with a notice when secrets are absent; a role without
  secrets skips itself. Secrets (repo, or `production-api` environment for the
  api): `STAGING_SMOKE_EMAIL`, `STAGING_SMOKE_PASSWORD`,
  `STAGING_E2E_{CONSUMER,ADMIN,SUPERVISOR,TRAINEE,HIRE_ADMIN,HIRE_CANDIDATE,PARTNER_ADMIN,PLATFORM}_{EMAIL,PASSWORD}`,
  `STAGING_E2E_ORG_SLUG`, `_HIRE_SLUG`, `_PARTNER_SLUG`,
  `STAGING_E2E_PLATFORM_TOTP_SECRET`; variable `STAGING_E2E_WEB_URL` on
  `production-api` (`STAGING_API_URL` already exists).
