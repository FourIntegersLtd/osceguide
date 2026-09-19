# The port: what is left, split into jobs

`platform-web` replaces `frontend/`. The frame is done and proven; most of the
screens are not. This is the audit and the split.

Each job below is sized for one agent in one session. They are drawn along the
tier boundaries, which is what makes them safe to run at the same time: a
capability may not import a domain or another capability, and a domain may not
import another domain — the linter fails the build otherwise. Two agents
working in different folders cannot silently break each other.

## Where things stand

| | Files | Lines |
|---|---|---|
| Old consumer arm `frontend/src/b2c` | 530 | 77,150 |
| Old institution arm `frontend/src/b2b` | 466 | 60,483 |
| `platform-web` today | 375 | 51,110 |

Backend endpoints wired by a screen: **76 of 180**.

### Done, and checked in a browser against a live API

The frame (workspace URLs, arms as data, one shell, the switcher, redirects,
middleware, error pages) · the public site (landing, per-exam pages,
institutions, legal) · the foundation (~40 primitives, 12 charts, the table,
modals, toasts, both token vocabularies, the full product stylesheet) · auth
(sign-in, register, forgot, reset) · the Partner arm · the marking-payload
reader on the backend.

### Not done

Everything else. The table below is the work.

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
`capabilities/authoring/`. Stations, station templates, feedback templates,
rubrics, exams, programmes. **One implementation for institution, partner and
staff**: the backend serves the same shapes under `/orgs/{slug}/…` and
`/platform/…`, and the capability takes its scope from `SurfaceContext`. 55
unwired endpoints — the single biggest block of unused backend.

### Wave 2 — after the job it names

Wave 1 is done: J1–J10 all landed, and so did the backend's `GET /me/performance`
(B1). J11 below is done too.

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

**J12 · Institution: results and reviews** — `b2b/components/features/feedback`
+ the reviews screens (2k) → `domains/assess/results/`. GP lead review, finalise,
sign-off, release. **J11 has landed**, so the slot navigation this hangs off is
there: every station row in `StationProgressList` links to its review. The
circuit-level finalise is already wired from the runner; what is left here is
the GP lead's own review, the sign-off and the release.
**Next job.**

**J13 · Institution: dashboard, live board, reporting** —
`b2b/components/features/dashboard` (0.8k) → `domains/assess/dashboard/`.
Org dashboard, the live board and its stream, the sitting report, cohort view.
**Needs J9** for the roster shapes it reads.

**J14 · Trainee and practice arms** — `b2b/components/features/{trainee,
practice}` (4.1k) → `domains/assess/trainee/`. A rostered trainee's sittings,
joining, their result, and an organisation's self-practice arm.

**J15 · Staff console** — `b2b/components/features/platform` (2.3k) →
`domains/platform/`. Org edit, memberships, audit log, platform-admin toggle,
and the authoring routes over J10.

### Backend jobs — independent of all the above

**B1 · `GET /me/performance`** — the endpoint J1 is waiting on. The hard part
is done and committed: `dashboard/performance.py` reads the engine's payload
into a score per domain, tested against all four seeded frameworks. What is
left is the service that walks a person's evaluated attempts, the schema, the
router, and a summary (pass/fail/critical rates) and trend line beside the
domain scores. Half a day.

**B2 · Tenant SSO** — `getSsoConfig` in the old client has no counterpart.
Blocks nothing today; sign-in works without it.

**B3 · The small gaps** — accessibility settings (extra reading time), photo
upload, achievements, contact messages, product feedback, public blog listing,
public statistics. Each is small; together they unblock the last corners of
J1, J4 and J8. See `docs/port-gaps.md`.

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
