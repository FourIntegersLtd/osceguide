# Ship features without breaking the rest

Status: implemented 2026-10-08 (5df56fd0, 3a763d13). Staging test world and its GitHub
secrets set up the same day (`e2e-staging-*` organisations). Left by hand: the Sentry alerts
(`docs/OPERATIONS.md`). Open: B-36 (bulk actions with no screen). Decided: staff of a
suspended org keep the live stream's 403. Not built: the `experience-audit` skill
(`fix-experience-gaps` covers audits until a new arm needs one). Written as a proposal after a deep dive (coupling map, bug history,
arm map, coverage). Nothing in
Parts 1-3 needs a new dependency or a database change; the two items that would are
marked "ask first".

## The goal

OSCE Guide will keep growing. A new feature must not quietly break an old one, and we
must never need another full audit. Each kind of bug gets a check that fails the
build the moment it is written, whoever writes it.

## What the deep dive found (the facts the plan rests on)

- 205 gaps, by kind (multi-label, from docs/EXPERIENCE-GAPS.md):
  state over time (suspended, revoked, retired, lapsed) 33; copy that lies 24;
  failed load shown as empty 20; control shown to a refused role 19; security or
  scope leak 18; missing or misleading email 18; dead route or nav 17; first page
  only 17; raw error code 16; invisible job failure 16; cross-arm 15; destructive
  action with no confirm or audit 12; concurrency 9.
- 13 rows were caused by an earlier fix. The dominant pattern: a check fixed in one
  gate and not its siblings (join, run, list each decide separately whether a
  revoked trainee may take part). The api has ~40 separate `ensure_*`/`may_*`/
  `require_*` gates and no shared "is this person still allowed here?" check.
- Four runner commits broke the build or tests outright (7fa4816, ad4b3b2,
  5fd1fca, edbf127). Lanes committed without running the slice's tests.
- BLOCKS rows by arm: institution 23 of 40, staff console 9, shared access/billing 6,
  hire 1, partner 1, consumer 0.
- Hire is two files (`surfaces/hire/surface.ts` + test); it renders assess's
  screens. Partner is 347 lines, no tests. There is nothing hire-specific to own.
- Hubs: identity (~22 incoming imports), catalog 17, attempts 14, tenancy 12,
  stations 11, notifications 10, entitlements 8. dashboard imports 15 slices.
  Workers reach the api only via HTTP `/api/worker/*`.
- Shared across arms: the attempt engine (attempts, voice, attempt-runner,
  station-runner, feedback, debrief) serves train AND assess (so hire). media,
  community, transcripts, help, authoring and account span 2-5 arms.
- Coverage holes: dashboard api has 0 http tests; results, reviews, sso, growth,
  media_production thin; web partner, fact-check, onboarding, transcripts, table 0
  tests; no component tests at all (runner is `node --test` on pure .ts).
- Ownership: unowned = health/ops, inbox, worker entry, attempt-runner,
  station-runner, debrief, feedback, hire and partner surfaces. Doubly owned =
  attempts, reviews, results, catalog, dashboard.
- Release path: merge → staging auto-deploy → manual promote gated on CI green +
  `/health` commit + a curl sign-in and dashboard read. No journey runs anywhere in
  CI or on staging. Sentry is wired in all three apps; no alert rules. No feature
  flags. Rollback is manual for api and web.

## Part 1: checks in CI, ranked by how many past bugs each would have caught

Each is one test file that fails with the list of offenders. The first run fails on
existing code: fix it or add it to an allow-list with a reason. Allow-lists only
shrink (a guard asserts the count never rises).

1. **Lifecycle matrix** (covers kind 1, and most "caused by a fix" rows).
   `api/tests/guards/test_lifecycle_matrix.py`: for each state (org suspended,
   contract ended, membership removed, trainee revoked, programme or exam retired,
   station archived, entitlement lapsed or refunded, account closed) × each
   operation (join, start, sit, mark, release, list `/me/*`, checkout, stream),
   assert the same answer. Build it from fixtures, parameterised. A grep guard
   requires every new status literal to appear in the matrix.
   Then, and only then, fold the sibling gates into one small check per subject
   (`org_active`, `membership_active`, `rostered`, `entitled`) that the existing
   gates compose. Not one mega-gate.
2. **Role per route, both sides** (kind 4, and the "supervisor sees a button that
   403s" family). api: extend `tests/guards/test_routes.py` so every route declares
   a minimum role and a lower role gets 403, including SSE streams. Export it to
   `openapi.json` as `x-capability`. web: `scripts/check-route-gates.mjs` fails on
   any mutating `api.ts` call used outside a `can(session, <same capability>)` or
   route guard. Start with write routes.
3. **Mechanical trio** (kinds 3, 7, 9):
   - `web/scripts/check-error-codes.mjs`: every code in `openapi.json` has a web
     handler or is in the "generic with reason" list.
   - `web/scripts/check-route-callers.mjs`: every `platformRequest` has a route;
     every web-facing route has a caller or is listed internal. Extend to nav
     `href`s and manifest `screenNames` resolving to a page.
   - eslint rule: ban `.catch(() => null|[])`, `failure={() => null}`, `useAsync`
     without a boundary. Lint `next_cursor` returned and ignored, and hard-coded
     `limit` with no cursor.
4. **Jobs, audits, idempotency** (kinds 10, 12, 13):
   - per job: force an exception; assert a terminal visible state, a user-visible
     flag and a staff retry route. Lint `except: log` with no state write.
   - every DELETE/archive/retire service calls `record_for_owner` (audit) and runs
     an in-use check.
   - every state-transition POST called twice (and concurrently) stays correct.
5. **Journeys in CI** (kind 11 and wiring). `ci-web.yml` starts the api (Postgres
   service, `seed_platform.py`) and runs `npm run e2e`. One journey per arm:
   train, assess, hire (employer org: nav resolves, candidate sees "My
   assessments"), partner, platform console. A role-matrix spec opens each page as
   each role and fails on any 403 or notFound. ~12 specs total; they catch wiring.
6. **Copy from constants** (kind 2, the only mechanisable slice of it): password
   length, TTLs, station counts, reading minutes come from one shared constant or
   the API's `PlanRead`; a grep guard flags duplicated numbers in `*.tsx`.

Coverage to fill while doing 1-5: http tests for dashboard, results, reviews, sso;
unit tests for web partner and transcripts. **Ask first:** component tests for
loading/error states need a test library (new npm dependency).

## Part 2: how Claude is organised

Three pieces, each one mechanism:

| Piece | Mechanism | Rule |
|---|---|---|
| Area notes ("what to know") | `.claude/rules/<area>.md` with `paths:` frontmatter | Follow the code's real coupling, not the product. Loads automatically when a session touches those paths. ≤150 lines each |
| Skills ("how to work") | `.claude/skills/<verb>/SKILL.md` | Named for actions, few |
| Owners ("who does it") | `.claude/agents/<area>-owner.md` | One owner per file. Owner = "you own these paths; read the rule file; prove with the verify skill" |

### Area notes (11), following the coupling clusters

1. identity-tenancy — identity, tenancy, sso, core/tenancy, web session + middleware
2. money — entitlements, billing, growth/referrals, partner surface, web account billing
3. attempt-engine — attempts, voice, the `/api/worker/*` contract, web attempt-runner,
   station-runner, feedback, debrief, transcripts, assessment/ workers
4. marking-results — rubrics, catalog (exams), results, reviews, engine prompts
5. exam-day — sittings, roster, circuits, dashboard org/trainee views, web domains/assess
6. station-content — stations, station_sets, templates, generation, authoring web
7. media-community — media, media_production, community, marketplace, peer_practice
8. tutor-ai — tutor_memory, assistant, help, onboarding, assistant worker
9. comms — notifications outbox, templates, inbox, public_site
10. staff-console — health/ops, domains/platform, staff-* capabilities, alembic
11. web-foundation — foundation/*, surfaces/* (incl. hire, partner), app/, learner
    dashboard, marketing

Hire and partner get journeys (Part 1.5), not notes: there is no code to annotate.

### Owners (7), one per file

| Owner | Notes it reads | Change |
|---|---|---|
| access-owner | 1, 2 | drop partner web (→ institution), keep growth api |
| institution-owner | 5, + hire and partner surfaces | gains hire/partner surfaces and their journeys; loses domains/platform |
| marking-owner | 4 | sole owner of reviews, results, catalog exams, attempts scoring files |
| attempt-engine-owner (renamed from voice-station-owner) | 3, 8 | gains runners, feedback, debrief, tutor-ai; attempts non-scoring files |
| content-owner | 6, 7 | unchanged |
| staff-console-owner (**new**) | 10 | health/ops, domains/platform, alembic, worker entry |
| web-foundation-owner (renamed from platform-web-owner) | 11 | gains learner dashboard api files, inbox web |

`.claude/OWNERS.md`: a path → owner table. `api/tests/guards/test_ownership.py` (or
a root script in both CIs) fails if any tracked source file matches zero or two rows.

### Skills

- `build-feature` (replaces `test-first-feature`):
  1. spec matrix (roles allowed/refused; each load: loading, empty, failed, paged;
     each action: success, each error code, double submit, stale; state over time;
     scale; out of scope);
  2. **arm check**: which arms render the files you touch (from the capability
     `surfaces` list); every such arm's journey runs before done;
  3. **sibling check**: grep every other gate that asks the same question; change
     them together, add the row to the lifecycle matrix;
  4. impact: grep callers, list the guards and journeys that cover them;
  5. failing tests at the lowest level per matrix row;
  6. smallest build (reuse first, no new layer without a second caller, delete
     what is now dead, no shims);
  7. prove with the owner's verify skill + journeys; `quality-reviewer` always,
     `reviewer` (opus) for auth, money, deletion;
  8. ledger: `docs/CORE-JOURNEYS.md` if a journey changed.
- `fix-bug`: reproduce with a failing test; fix the root cause; **name the kind
  (1-13 above) and the Part 1 check that should have caught it; if none, add or
  extend one in the same change**; commit with "caused by <sha>" when a fix
  introduced it.
- `verify-*`: one per owner (rename verify-voice-station → verify-attempt-engine;
  add verify-staff-console). Keep web `verify`.
- `experience-audit`: for a new arm or big feature only, scoped to it.
- Retire `fix-experience-gaps` once the gaps list is closed.

### Hooks and the runner

- `quality-gate.sh`: diff only the files this session edited (PostToolUse
  Edit/Write log), not the working tree. Stops it nagging about other sessions.
- Optional, warn-only Stop hook: app code changed, no test file changed.
- Night-runner `prompt.md`: a lane runs its slice's tests and `make lint` before
  committing. (Four commits broke the build this week.)

## Part 3: catching what reaches staging and production

Today the promote gate checks sign-in and the dashboard by curl; hire, partner,
console, billing, voice, SSO and invitations reach production unverified.

1. **Staging smoke in CI**: wire the existing `web/scripts/smoke.mjs` (client vs
   api routes and permissions) to run against staging after each deploy. Cheap,
   no data created.
2. **Staging journeys before promote**: the Part 1.5 specs, run by `promote-*`
   against staging with a dedicated test organisation and seeded accounts
   (secrets in GitHub). Specs clean up what they create. Last in the order: it
   needs the test org and secrets set up.
3. **Sentry alerts** (configured once in Sentry, documented in
   `docs/OPERATIONS.md`, no tooling): new issue in production; error-rate spike
   per app; `score_attempt` failure; outbox message abandoned after 6 attempts.
4. **Rollback in one command**, written down: Railway redeploy for the api, Vercel
   instant rollback for web, the workers' existing rollback input.
5. No feature-flag system until a second real need appears.

## Order of work

1. After the runner's push is green: Part 1.3 (mechanical, `worker`) + the hook and
   runner-prompt fixes. One session.
2. Part 1.1 lifecycle matrix (design step, opus) and Part 1.2 role table. One
   session each.
3. Part 2: OWNERS.md + ownership guard, rules files, renamed owners, the two skills.
   One session, mostly moving text.
4. Part 1.5 journeys in CI + Part 3.1 staging smoke. One session.
5. Part 1.4, 1.6, coverage holes. Then Part 3.2-3.4.

## Done means

- `make ci` and `npm run ci` include every Part 1 check and pass on `main`.
- `ci-web.yml` runs the per-arm journeys; `promote-*` runs the staging smoke.
- Each check has been proved by reintroducing one bug of its kind and watching CI
  fail, then reverting.
- Every tracked source file has exactly one owner, and CI says so.
- AGENTS.md points to `build-feature` and `fix-bug` as the way to work.
