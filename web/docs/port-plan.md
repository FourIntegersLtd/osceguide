# The port, and the jobs it was split into

`platform-web` replaces `frontend/`. This was the audit and the split; it is
now the record. Every job has landed — see "Where things stand".

Each job below is sized for one agent in one session. They are drawn along the
tier boundaries, which is what makes them safe to run at the same time: a
capability may not import a domain or another capability, and a domain may not
import another domain — the linter fails the build otherwise. Two agents
working in different folders cannot silently break each other.

## Where things stand

**The port is finished.** J1 to J15 have all landed; the table below is the
record of what each one did, not a queue.

| | Files | Lines |
|---|---|---|
| Old consumer arm `frontend/src/b2c` | 530 | 77,150 |
| Old institution arm `frontend/src/b2b` | 466 | 60,483 |
| `platform-web` when this plan was written | 375 | 51,110 |
| `platform-web` now | 592 | 76,410 |

Two old arms totalling 137,633 lines are one client of 76,410, and that is
before deleting `frontend/`.

### What is left

Not screens. Every remaining item is something `platform-api` does not serve,
and each one is written down in `docs/port-gaps.md` beside the screen that
wants it. The two backend jobs below, B2 and B3, are the rest.

---

## The jobs

Dependencies are stated. Anything with no dependency can start now, and jobs in
the same wave do not touch each other's files.

### Wave 1 — can all start immediately

**J1 · Consumer dashboard** — *the most valuable single screen*
Old: `b2c/components/{sca,plab,casc,ortho}/dashboard` (8.4k lines across four
near-identical screens). New: `domains/train/dashboard/`.
Collapse the four into one `ExamDashboard` driven by an `examConfig` per exam —
domain labels, thresholds, section order, copy. PLAB, CASC and Ortho differ by
about 270 lines of config across a thousand; SCA is genuinely richer (competency
hero, insights, weekly trend) and keeps its own sections behind the same config.
Verify each exam's rendered output against the old screen before deleting it.
**Needs first:** `GET /me/performance` (job B1). Build the layout and the parts
`/me/dashboard` already serves; wire the charts when B1 lands.

**J2 · Mocks** — `b2c/components/shared/mocks` (2.6k) → `domains/train/mocks/`.
List, customise, rules, runner, end, review. Replaces the rebuilt `Mocks.tsx`
and `MockDetail.tsx`. Endpoints exist: `/me/station-sets*`.

**J3 · Station library and the runner** — `b2c/components/shared/stations`
(3.3k) → `capabilities/stations/`. Browse, filter, detail, and the consultation
runner itself. Absorbs the rebuilt `StationLibrary`. Endpoints exist.

**J4 · Feedback, debriefs, transcripts** — `b2c/components/shared/{feedbacks,
debriefs,transcripts}` (2.1k) → `capabilities/feedback/`, new
`capabilities/debrief/`, new `capabilities/transcripts/`. Endpoints exist
except the debrief write (`/me/station-sets/{set}/entries/{entry}/debriefs`,
which does exist — wire it).

**J5 · Study material** — `b2c/components/shared/{slides,summary,media,blogs}`
(4.3k) → `capabilities/media/`. Decks, the A-to-Z, articles, episodes. One
capability, four kinds. Endpoints exist.

**J6 · Community** — `b2c/components/shared/{community,comments}` (2.1k) →
`capabilities/community/`. Questions, answers, station comments. Endpoints
exist; `/stations/{id}/comments` is unwired.

**J7 · Peer practice** — `b2c/components/shared/{marketplace,human-practice}`
(7.2k) → `capabilities/peer-practice/`. The queue, the marketplace, the paired
session. Largest consumer job after the dashboard. Endpoints exist.

**J8 · Account** — `b2c/components/shared/{settings,users,achievements}` (5.9k)
→ `capabilities/account/`. Profile, password, referrals, receipts, purchase
(`/billing/checkout` is unwired and is the only way anybody can pay), payment
return pages. Achievements has no backend — see `port-gaps.md`.

**J9 · Institution: team and roster** — `b2b/components/features/team` (4.3k) →
`domains/assess/team/`. Invite, change role, revoke, restore, add trainee, CSV
import, cohorts, groups, grant access. 15 unwired endpoints across `tenancy`
and `roster`.

**J10 · Authoring** — `b2b/components/features/{content,stations,templates,
feedback}` + `b2c/components/admin` + `shared/aiauto` (9.9k) → a new
`capabilities/authoring/`. Stations, station templates, rubrics (AI structure +
examiner `marking_layout`), exams, and org programmes.
rubrics, exams, programmes. **One implementation for institution, partner and
staff**: the backend serves the same shapes under `/orgs/{slug}/…` and
`/platform/…`, and the capability takes its scope from `SurfaceContext`. 55
unwired endpoints — the single biggest block of unused backend.

### Wave 2 — after the job it names

Every job in both waves has landed, and so has the backend's
`GET /me/performance` (B1). Each is recorded below with what it wired and what
it could not.

**J11 · Institution: the live session runner** — **done.**
`b2b/components/features/sessions` (15.2k, 94 files) → `domains/assess/sessions/`
(twelve files, all under 300 lines). One `useCircuitRun` hook fed by the console
stream; one screen for both modes, because a training circuit and an examination
turned out to differ only in the turn strip and who may be added to it. The
rebuilt `CircuitConsole` it replaces is deleted.

Wired: `jump-to`, `redo-station`, `append-trainees`, `auto-advance`,
`interventions`, `review/finalize`, and a reason on every override — the backend
keeps it beside the action, which is what makes an interrupted examination
defensible afterwards. `edit-lock` stays unwired on purpose (the console frame
already carries `editable` and `edit_block`).

Not ported, and why, in `port-gaps.md`: the supervisor's microphone, camera and
video tiles (the observer token is subscribe-only by construction, and nothing
in this product publishes video), the reading brief, and the whole LiveKit timer
data channel — the clock is the server's now.

**J12 · Institution: results and reviews** — **done.**
`b2b/components/features/feedback` + the reviews screens (2k) →
`domains/assess/results/` (eight files). The sitting report carries the whole
examination in one request, so the old cohort summary, candidate pack per
person and probe per slot are one screen with disclosures.

Wired: the GP lead's review (revisioned, with the conflict refusal surfaced),
the slot's agreed ratings, the cohort ranking, and the decision workflow as a
PUT that actually saves.

Three things in the rebuilt screens did not work and now do — recording a
decision was a POST against a PUT route, "borderline" was offered against a
four-value enum, and the evidence a release is re-checked against was never
sent, so that safeguard compared two empty objects. There is also no
`GET .../reviews/mine`, which the old screen called anyway: a reviewer's own
draft never came back. All in `port-gaps.md`, with what the backend still owes:
a bulk release, a notification on release, a cohort export, and optimistic
concurrency on a decision.

**J13 · Institution: dashboard, live board, reporting** — **done.**
`b2b/components/features/dashboard` (0.8k) → `domains/assess/dashboard/`.

The two old dashboards — an administrator's and a supervisor's, chosen by
reading a role string — are one screen whose parts are chosen by what
`/me/capabilities` grants, so somebody who is both sees both halves.

The exam-day board is new: `GET /orgs/{slug}/live` and its stream were among
the endpoints nothing called, and they answer the question the old client could
not — "how is this morning going" — which used to be answered by walking
between rooms. Rows are ordered by trouble and then by whoever runs out of time
first, and a consultation running with nothing recording it is on the board
while it happens rather than discovered afterwards.

The sitting report and the cohort view landed with J12.

**J14 · Trainee and practice arms** — **done.**
`b2b/components/features/{trainee,practice}` (4.1k, 29 files) →
`domains/assess/trainee/` (nine files). A rostered trainee's sittings, joining,
their result, their station records, and the organisation's self-practice arm.
The rebuilt `TraineeHome` and `MyResult` it replaces are deleted.

One feed does most of it. `/me/sittings` carries every sitting *and every slot*
this person owns and it streams, so the overview and the sitting page are two
projections of one subscription — where the old arm had a list endpoint, a
detail endpoint polled every five seconds, and a filter in the browser over the
organisation's own session list.

Joining is one component used by both. The old arm decided whether somebody
could go in from five booleans (`isSelfLedTraineeSession`, `examSelfLedTimer`,
`isDirectPractice`, `isSoloPractice`, `partnerSelfLedTraining`) across a join
page, a live-session component and four pre-join states; the backend answers it
with `can_join`. The automatic join during reading is kept, and the reason is
in the file: the patient is dispatched on the server's clock and needs the room
to already exist.

Self practice is one screen where there were three — self practice, a
direct-practice home and its station list — plus a `mock/` folder with its own
timer, LiveKit consultation and five tabs. All of them list an organisation's
published stations and sit one alone, which is `POST /attempts` over
`capabilities/attempt-runner`. `self_practice` was missing from `AttemptKind`
and is the one kind that route actually accepts; it is there now.

Also wired: `GET /orgs/{slug}/stations` as a trainee (the predicate behind
`OrgReader` admits one), and the `attempt` screen on Assess, so an institution's
candidate can read a station back — the marking and the transcript, both off the
attempt on their slot.

Not ported, and why, in `port-gaps.md`: **a candidate cannot read the circuit
feedback their supervisor published** — `review/finalize` writes it and nothing
reads it back for the person it is about, which is the largest gap this job
found — nor their own slot review; the practice *mock* (pick n stations, sit
them back to back) is a station set and mounting `domains/train/mocks` on Assess
is a product decision rather than a port; and there are no candidate microphone
or camera controls, for the same reason the supervisor has none.

**J15 · Staff console** — **done.** The last of them.
`b2b/components/features/platform` (2.3k, 9 files) → `domains/platform/` (eight
files). The overview, the tenant directory, an organisation's own screen and
the user search. It replaces the rebuilt `Console.tsx`, which was one file
holding three screens.

Wired: provisioning, renaming, changing a type, the contract dates, suspend and
restore, seating a new tenant's first member, searching accounts by address
with paging, and the platform-admin grant. The authoring routes over J10 needed
no work beyond checking them: `SurfaceShell` appends the capability registry to
every arm's nav, so `/staff/authoring` and `/staff/settings` are already there
and were verified in a browser.

Two of the old screens have no backend to stand on and are not ported: the
audit log and the platform team. Both are recorded in `port-gaps.md` with the
one-line backend change each would need — `OrgAdmin` is declared
`allow_platform_admin=False`, so a console admin may read an organisation for
support and inherits none of its powers, and `UserSummary` does not say whether
an account is a platform admin. The grant is therefore two explicit acts rather
than a toggle whose position would be a guess.

Deleting a tenant is **deliberately** gone rather than missing: the backend has
no delete, because an organisation's rows include candidate results that have
to stay defensible. Suspension is the reversible mechanism.

One defect found in a browser and fixed: filtering the directory to a status
nothing was in said "No organisations yet" on a platform with six of them.

### Backend jobs — independent of all the above

**B1 · `GET /me/performance`** — **done**, and it was already done before this
sweep looked: the router, the schema (summary, domain scores and trend line),
the service that walks a person's evaluated attempts, and 27 tests, all in
`app/features/dashboard`.

**B2 · Tenant SSO** — **the discovery half is done** (platform-api commit
c04411e). `organization_sso` and `organization_sso_bindings` hold what the old
client hardcoded in its bundle, and `GET /auth/sso/sign-in?host=…` or `?email=…`
answers a sign-in page without a token. `GET|PUT /platform/orgs/{slug}/sso`
configures it, platform admin only.

**The sign-in itself is deliberately not built.** Who verifies an identity is an
open decision — the retiring backend brokered through Clerk to Microsoft, and
neither backend in this repo has a flow to port — so `sso_only` is a display
rule and nothing refuses a password login yet. See platform-api's
`docs/OPEN-QUESTIONS.md`, S-1.

Frontend follow-up when somebody wants it: the sign-in page calls
`/auth/sso/sign-in` with `window.location.hostname` and hides its password form
on `sso_only`.

**B3 · The small gaps** — **five of seven done** (platform-api commit b1c597d):

- **public blog listing** — `GET /media` and `GET /media/{slug}` no longer
  require a bearer. `landingBlogs.ts` can ask again.
- **public statistics** — `GET /site/statistics`, cached for ten minutes.
  `fetchLandingStats()` returning `null` is one function body away from working.
- **contact messages** and **product feedback** — `POST /site/messages`, with a
  platform-admin inbox behind it. The "Help Us Improve" section can go back into
  `landingSections`.
- **accessibility (extra reading time)** — `users.extra_reading_percent`, on
  `/me` and settable through `PATCH /me`. It applies to a person's own practice
  and **not** to a circuit's clock, which serves everybody on it — see S-2.
- **exam date** — `users.exam_date`, which the dashboard countdown and
  `ExamWishes` both needed and neither had.

Still unbuilt, each for a reason in platform-api's `OPEN-QUESTIONS.md` (S-3):
**achievements** needs a decision about what a streak is when attempts are the
only progress record, and **photo upload** needs an object store before it needs
code.

---

## The port is done

J1 to J15 have all landed, and so has B1. `platform-web` is the client; nothing
is waiting on `frontend/` any more.

What is left is not porting. It is the backlog in `docs/port-gaps.md`: B2 and
B3 above, and the per-screen gaps each job recorded — every one of them a thing
the backend does not serve yet, written down beside the screen that wants it.

The two sections below are kept as they were. They are how each of these jobs
was run, and the next person adding a screen should work the same way.

---

## What every job must do

The rules are the same for all of them, and the first two are the ones that
were got wrong before.

1. **Same UI, same behaviour. The code may be rewritten.** The old screen is
   the specification for what it looks like and does; rewrite the
   implementation wherever the old one fetches inline, duplicates another
   screen, or fights the tiers. A reader must not be able to tell from the
   browser which path was taken.
2. **Check the ported fonts and tokens render.** The product stylesheet and the
   three faces are loaded now, so a ported screen should look right
   immediately. If it does not, something is missing rather than the screen
   being ugly.
3. **No network call outside an `api.ts`.** Lint fails otherwise.
4. **No literal route prefixes.** Use `hrefFor()` from the surface context.
   Lint fails otherwise.
5. **Anything the backend cannot serve goes in `docs/port-gaps.md`**, never a
   `TODO`.
6. **Delete the rebuilt screen it replaces** in the same commit.
7. **Verify:** `npm run ci`, then the screen side by side with the old app —
   `frontend/` on :3000, this on :3100, same seeded account. Add its endpoints
   to `scripts/smoke.mjs`. For anything touching routing, session or shells,
   run `node scripts/walkthrough.mjs`.

## Running them in parallel

Wave 1 is ten jobs that touch ten disjoint folders. The shared files are
`capabilities/registry.ts` (one line per new capability),
`surfaces/*/surface.ts` (one nav entry) and `src/app/app/[workspace]/` (one
page file per new route) — small, mechanical, and the only places two jobs can
collide. An agent should add its own line and expect to rebase.

The tier linter is the real protection: a job that reaches outside its folder
fails the build rather than quietly coupling two features together.

---

## J16 · Consumer parity — **in progress**

Raised after walking the signed-in consumer arm against `frontend/` and finding
three things wrong. The first two are done; the third is the current job.

**The navigation did not match.** It was one flat list carrying an "Access"
item that rendered the same panel Settings already showed as a tab, and a
"Transcripts" item for something that is a panel of the consultation screen
rather than a destination. It is now the retiring client's three headed groups
— Practice, Connect, General — in its order, with the study library kept where
the user asked for it, billing back under Settings, and a footer carrying the
upgrade button, the person's name and which exam they are sitting. Settings has
its Preferences and Exam tabs back.

**Exam dropdowns were everywhere.** See `port-gaps.md`, "The active exam".
One answer from the backend, one switcher, no per-screen selectors — and the
backend now refuses browsing, queueing, offering a slot or building a set for
an exam somebody does not hold, where only `POST /attempts` checked before.

**The station flow — done.** The old screen is one tabbed container — 1.
Reading time, 2. Consultation, 3. Management, 4. Feedback — and it is that
again: `domains/train/station/`, over three new pieces in `attempt-runner`
(`StationBrief` per exam, `ManagementPlan`, the two-column `ConsultationScreen`
and its panel) which the institution arms can mount too. The timer is the
foundation's, persisted per attempt.

The attempt is created when the station *opens* rather than when the patient is
called, because the brief is read off the attempt — which is what makes it the
candidate's to see. That is the one real design change, and it is why
`useStationAttempt` keeps the id in `sessionStorage`.

`/mocks/{id}/complete` is back, with the feedback-status list the old MockEnd
had. `AttemptResult` and `MockStationRunner` are deleted.

**Three things driving the real app caught that CI did not:** opening a station
created *two* attempts (React re-invokes effects; the storage guard could not
see the race), reviewing one picked the newest attempt rather than the newest
*finished* one and so showed an empty Management tab, and `/app/me/access`
404ed because the redirect table only covered the pre-workspace spelling — and
then double-encoded its query when it did match.
