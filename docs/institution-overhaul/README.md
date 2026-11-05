# Institution arm overhaul: phase briefs

One orchestrating chat hands each phase to its owner agent, **one phase at a time**. Each brief
below is self-contained: an agent that has never seen this project can do its phase from the
brief plus the files it names. The orchestrator checks each result against the boards before
the next phase starts, and ticks the ledger at the bottom.

## Shared context (every phase reads this)

**What OSCE Guide is.** A medical exam-practice platform. Its institution arm ("assess") is
used by medical schools to run OSCE exams: an admin sets up exams and stations, adds trainees
and supervisors, schedules a *sitting* made of *circuits*, supervisors run each circuit live,
stations are marked (AI and human), and results are signed off and released. The hire arm is
the same product for employers, in employer words. Stack: Next.js App Router (`web/`), FastAPI
(`api/`). Read `AGENTS.md`, `web/AGENTS.md` and `web/docs/DESIGN.md` first.

**Why we are changing it.** New admins cannot tell what to do first. The overhaul makes the
order obvious (Home setup assistant, one "Exam" noun, a Schedule-a-sitting wizard, People in
one place) without removing anything.

**Source of truth.**
- `docs/institution-overhaul/PLAN.md`: the full plan (sections Redesign 1-10 and Build phases).
- `docs/institution-overhaul/boards/*.dc.html`: one design board per screen. Open the file
  and read it as HTML. Each board has:
  - tabs across the top: every tab is a screen or a state you must build;
  - boxes (`<sc-if value="{{ d_x }}">`): every one is a `Modal` / `ConfirmModal`;
  - a "What changed" note: the only deliberate differences from today's app;
  - a **Build spec** fold at the bottom: route, who sees it, owner, files to change,
    every API call with today's caller, and the build steps. Follow it literally.
- `docs/institution-overhaul/boards/BuildGuide.dc.html`: the rules for turning a board into code.
- **`docs/institution-overhaul/design/<Board>.md`: read this first.** The same board as plain
  text: one section per tab and per dialog, every label exactly as drawn, buttons as `[..]`,
  inputs as `‹input: ›`, plus the build spec. Build every section; tick each off in your report.

**Hard rules.**
1. **No feature is removed.** Every control on today's screen stays reachable. If today's
   screen has something the board does not show, stop and report it; do not drop it.
2. **Keep the design language.** `web/docs/DESIGN.md`, `foundation/ui` components, existing
   tokens. No new palette, type size or component family.
3. **No api change.** Every endpoint already exists and is listed in the board's Build spec.
   No new endpoint, schema, migration or dependency. If one seems needed, stop and report.
4. **Copy is the spec.** Use the board's words exactly. Nouns go through
   `web/src/domains/assess/useAssessWords.ts` / `vocabulary.ts` so hire reads its own words.
5. **Old URLs keep working** (redirect or same page), e.g. `/team`, `/programmes`, `/stations`.
6. **No polling.** Live data uses the existing SSE streams (`useMeEvents`, `*/stream`).
7. **Do not touch other work.** The tree has uncommitted exam-day changes that are not yours.
   Never revert, reformat or stage files outside your phase. Do not commit or push.
8. Work through the `build-feature` skill: failing test first (Testing Library, literal
   expected words), smallest build, then your verify skill and the web `verify` skill.
9. Stay inside your phase's boards and files. If you need a file another phase owns, report it.

**Proof required before reporting done.**
- `cd web && npm run ci` passes; `npm run e2e:assess` passes (plus the hire e2e specs and
  `roles/role-matrix.spec.ts` where the phase touches nav or words).
- The web `verify` skill run against a seeded org (`node web/scripts/seed-demo-org.mjs`):
  every tab of every board in your phase visited in a real browser, as each role the board
  names. Keep the screenshots; list their paths.
- A parity table: every control on today's screen → where it is now.

**Report format (10-30 lines).** Files changed (`path:line`); tests added; proof run and
result; the parity table; anything you could not do and why; anything that looked like it
needs an api change.

**Running in parallel.** Phases run side by side, each in its own git worktree. So:
- Edit only your phase's files. `web/src/surfaces/*/surface.ts`, `vocabulary.ts` and
  `useAssessWords.ts` belong to Phase 1 only. If you need a menu or word change, list it in
  your report; Phase 1 applies it.
- Do not start dev servers, seed databases or run the browser `verify` skill (parallel runs
  collide on ports and the shared Postgres). Prove with unit/component tests, `npm run ci`
  and, for api-touching checks, `poetry run pytest` on the relevant tests. The orchestrator
  runs the browser verification after merging your worktree.
- Commit your work on your worktree's branch (that is the hand-off; it never reaches `main`
  without the orchestrator). Do not push.

Node is not on the default PATH: `export PATH="$HOME/.nvm/versions/node/v22.22.3/bin:$PATH"`.

---

## Phase 0: Baseline (institution-owner)

**Goal.** Record what exists today, so later phases can prove nothing was lost. No code changes.

1. Seed a demo org (`node web/scripts/seed-demo-org.mjs`) and run the app (api `make start`,
   web `npm run dev`).
2. With the web `verify` skill, screenshot every institution screen as org admin, supervisor,
   trainee and hire admin: dashboard, sittings (list, new, detail, circuits new/edit),
   circuit console, live, results (index, sitting results, slot review), trainees, team,
   programmes, authoring (every section and its new/edit screens), stations, reporting,
   settings, trainee home/sitting/result/review/practice, partner dashboard.
   Save to `docs/institution-overhaul/baseline/<role>/<screen>.png`.
3. Write `docs/institution-overhaul/baseline/INVENTORY.md`: for each screen, every button,
   tab, filter, row action, dialog and empty/error state, with its exact label. This is the
   parity checklist all later phases tick.
4. Run `npm run e2e:assess` and the hire specs; record pass/fail per spec. Walk
   `docs/CORE-JOURNEYS.md` ASSESS-1..6 and HIRE-1..2 and record each step's result.

**Done when** the inventory exists and every journey's result is recorded.

## Phase 1: Words, menu and Home (web-foundation-owner, then institution-owner)

**Boards:** `Main`, `Today`, `SupervisorHome`, `HireHome`. PLAN sections 1, 2, 3 and 9.
- Vocabulary: Exam, Station, Station layout (optional), Sitting / Assessment (hire),
  Circuit, Supervisor, Year group (cohort), Group, Mode wording. In `vocabulary.ts`.
- Menu sections in `web/src/surfaces/assess/surface.ts` and `surfaces/hire/surface.ts`:
  Home; Run: Sittings, Now running, Results; Organise: People, Exams; Insight: Reporting;
  Settings. Remove the duplicate Stations and Programmes items; their URLs still work.
  Keep `surfaces/registry.test.ts` passing.
- Home: setup assistant (5 steps, one at a time, "Step N of 5", "Continue setup") built from
  the flags the dashboard api already returns; afterwards "Today". Supervisor home.
- Every empty state links to its fix; every disabled primary button says why.
**Not in this phase:** the Exams hub tabs (phase 2), People merge (phase 4).

## Phase 2a: Exams hub, exams and programmes (content-owner; institution-owner for programmes)

**Boards:** `Exams` (tabs Exams, Programmes, Empty and read-only states), `AdoptExam`,
`NewExam`, `ExamSettings`, `ExamDetail`. PLAN section 4.
- Rename the Authoring page to Exams, Exams tab first; existing section URLs keep working.
- New exam sheet: create exam → publish → create programme → activate, with a resumable
  state naming the failed step. Exam status chip (Draft / Needs a marking scheme / Ready to
  schedule / Not available). "Available for scheduling" switch = programme activate /
  retire / reactivate.

## Phase 2b: Stations and station layouts (content-owner)

**Boards:** `Exams` (tabs Stations, Station layouts), `NewStation`, `CreateStation`,
`ImportStation`, `LayoutBuilder`, `StationBuilder`. Mostly today's screens moved under Exams
with the exam preselected; check every state on the boards exists and matches.

## Phase 2c: Marking schemes (marking-owner)

**Boards:** `Exams` (tab Marking schemes), `SchemeVersions`, `MarkingScheme`. Parity check
plus NewExam step 2 ("pick, copy from OSCE Guide, or write new", returning to the sheet).

## Phase 3: Scheduling and exam day (institution-owner)

**Boards:** `Sittings`, `ScheduleSitting`, `Sitting`, `EditCircuit`, `LiveBoard`, `Console`,
`TraineeSitting`. PLAN sections 5 and 6.
- Schedule-a-sitting wizard (6 locked steps) calling create sitting then `circuits/bulk`
  (formal) or `circuits` (training); retry state if circuits fail after the sitting exists.
- Sitting page: one primary action from `sittingSteps.ts`; edit gains year group.
- NewCircuit / EditCircuit rebuilt from the wizard's step components.
- Console and live board: wording and states per the boards; no behaviour change.

## Phase 4: People (institution-owner; access-owner for invitations)

**Boards:** `People`, `AddPeople`, `AcceptInvite`, `SignIn`. PLAN section 7.
- One People page (Trainees, Staff, Groups and year groups, Exam access, History); `/team`
  still resolves. One Add people sheet. "Move to year group" label fix; separate group action.
- Staff bulk revoke through the existing `memberships/bulk/revoke` route.
- Exam access tab uses the existing practice-access routes only if PLAN says so; otherwise
  report and leave it.

## Phase 5: Results and review (marking-owner, institution-owner)

**Boards:** `Results`, `SittingResults`, `SlotReview`, `CircuitReview`, `TraineeResult`,
`TraineeReview`, `Trainee`, `SelfPractice`. PLAN section 8.
- Results index leads with "Needs your attention"; supervisor "Stations to review" on Home
  from existing reads. Every other control is a parity check.

## Phase 6: Settings and Invoices (access-owner) — money: the user reviews it

**Boards:** `Settings`, `Invoices`. PLAN section 10. Invoices tab: list, detail and PO number
through the existing `/orgs/{slug}/invoices*` routes. Needs `/security-review` and the user's
review before it is called done.

## Phase 7: Docs (institution-owner)

Update `docs/CORE-JOURNEYS.md` steps, add/close `docs/EXPERIENCE-GAPS.md` rows, and the
product guide (`docs/guides/how-osce-guide-works.html`, `make product-guide`).
Reporting and Partner boards are parity checks only.

---

## Authorisation (user, 2026-11-05)

Work autonomously until every screen on the boards is built, following the designs and the
flow, and merge each reviewed phase to `main` and push it (user: "push to main, no live
users"). Never push the unrelated uncommitted exam-day changes in the tree; never force-push.
Ask few questions; record judgement calls below. Phase 6 (money) is merged after
`/security-review` and flagged for the user's read when they return.

## Judgement calls

- (orchestrator) Browser verification runs after each merge, in the main tree, one at a time.
- (2b) NewStation chooser is org-only; on an org, the AI card says a layout comes first (CreateStation.md: AI appears once a template is chosen).
- (6) Invoices: Settings tab holds the "Open invoices" link card; list and detail are on /settings/invoices.
- (3) Training-mode breaks not built by design (training has no breaks; the exam break is stored in `exams.settings.default_break_minutes`, no migration); bulk create defaults the name prefix to "Exam".

## Ledger (the orchestrator updates this)

| Phase | Status | Proof | Notes |
|---|---|---|---|
| 0 Baseline | done (b7ab963d) | inventory, e2e results | ASSESS-2 failing before our changes |
| 1 Words, menu, Home | merged (eeb84b09) | npm run ci; review running | |
| 2a Exams and programmes | merged | npm run ci, reviewer | see judgement calls |
| 2b Stations and layouts | merged (2f471167) | npm run ci, reviewers | |
| 2c Marking schemes | merged | npm run ci, reviewers | |
| 3 Scheduling and exam day | built, in review | npm run ci | |
| 4 People | merged (3bdec4ec) | npm run ci, reviewers | |
| 5 Results and review | merged | npm run ci, reviewers | |
| 6 Settings and Invoices | merged | npm run ci, security review clean; user to read (money) | |
| 7 Docs | not started | | |
| Browser verification | not started | | every merged phase |
| Final 41-board audit | not started | | |
