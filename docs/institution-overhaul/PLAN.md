# Plan: Institution arm, audit and redesign of its screens and flow

## Context
Users say the institution arm is too hard to use. A new admin cannot tell what to do first, and the nouns overlap:
- exam, programme, sitting, circuit and session;
- template, station and case;
- cohort and group;
- supervisor, lead and examiner.

The real order of work is marking scheme → exam → programme (and activate it) → station template → stations → people → sitting → circuit. Nothing outside one dashboard card teaches that order, and the sidebar runs in the opposite direction.

The old B2B was easier to follow. It had 5 nouns, a checklist showing one step at a time ("Continue setup"), a single wizard with locked steps for creating a session, header buttons that changed with state, and a help panel on every page.

The user also asked whether the product guide is accurate. That is the "How OSCE Guide Works" PDF in the repo root, a copy of `docs/guides/how-osce-guide-works.html`, published at https://claude.ai/artifact/NHJAJk1fgc968xssyvn7F8.

The outcome is a redesign of the institution arm's screens and flow, done the way Apple would approach it: one clear model, progressive disclosure, never a dead end.

## Hard rules (user, 2026-11-05)
1. **No feature is removed.** Every item in the feature inventory (below) stays reachable. Hiding something behind progressive disclosure is fine. Losing it is not.
2. **Keep the existing design language.** Use `web/docs/DESIGN.md` as it stands, with the existing `foundation/ui` components, assess and hire skins and semantic tokens. No new palette, type scale or component family.
3. **The UI changes; the api does not.** The exception is the invoices view, which uses routes that already exist. Collapsing exams and programmes is done by the screens calling existing endpoints, because `uq_org_programmes_org_exam` (`api/app/features/catalog/models.py:104`) guarantees one programme per exam.

## Decisions (user answers)
- **Treat exam, marking scheme and programme as one "Exam".** The programme becomes an "Available for scheduling" switch. The Programmes and Marking schemes lists stay reachable.
- **Design boards first.** A clickable artifact of every new screen gets the user's sign-off, then the build goes in phases.
- **Add these missing screens:** Team bulk revoke (gap B-36), editing a sitting's cohort after creation, and an org invoices view with a PO number. Invoices touch money, so the user reviews them. The two-step sign-in policy toggle is out.

## Product guide: accuracy verdict (to report and fix)
The guide is mostly accurate, and its refusal rows pass `make product-guide` (285 of 285). It is not up to date: it was checked against `31a5e741` (8 Oct), 185 commits ago, and its header still says "277".

**Wrong claims, to correct:**
1. "A school connects its own sign-in." Only platform staff can configure SSO (`api/app/features/sso/router.py:149,244`). The school sees its status only.
2. "Someone with a password gets a reset link instead." The resend is refused with `invitation_not_pending` (`tenancy/service_memberships.py:217-239`).
3. "A supervisor runs a circuit only when leading it." Any staff member can run any circuit (`sittings/router_run.py:35-64`). Only review and transcript access are limited to the lead.
4. "A senior review has a reason of up to 4,000 characters." The 4,000 limit belongs to the decision rationale (`results/schemas.py:34`).
5. "A circuit's review is finalised once every review is done." Finalising is a manual "Publish circuit feedback" (`reviews/router.py:210-237`).
6. "Timings are set by the sitting." They are set per circuit (`sittings/models.py:80`).

**Outdated claims:**
- Breaks now have a length each, 1 to 60 minutes.
- Only mode, programme and type lock once a sitting starts. The name and date stay editable.
- SCIM tokens are issued by the org admin, with no SSO needed first.
- Reporting covers more than exam sittings: there is an org Reporting page, a sitting report, a CSV export and a readout export.
- Chapter 9's "one at a time" claims are stale, because trainee bulk actions and CSV team invites now exist.
- A partner admin cannot sign off.

**Missing from the guide:**
- The "Now running" live board.
- Bulk exam circuits, adding a group or cohort to a circuit, reordering stations, and late joiners on training circuits.
- Result preview before release, the result PDF, bulk release, back-to-draft, and the candidate's acknowledgement.
- The Results page tabs.
- The org two-step sign-in status and SCIM tokens in Settings.
- Adopting an OSCE Guide exam.
- The Exam access tab.
- The temporary password option.
- Tolerant CSV import (BOM, delimiter detection, "create those cohorts").
- Station approval and per-plan station limits.
- The Self practice and Practice sessions entries for trainees.

## Deliverables
1. **Audit and redesign spec as a Claude Doc**, "Institution arm: audit and redesign". Sections:
   - verdict;
   - the real model, and the menu set against it;
   - a step-by-step walkthrough as a new admin, with `path:line` and exact labels;
   - the old B2B side by side;
   - a gap register of about 40 rows, cross-referenced to `docs/EXPERIENCE-GAPS.md` IDs;
   - glossary;
   - the redesign (below);
   - the guide verdict;
   - a feature parity checklist;
   - refusal codes by step.
2. **Design boards as an HTML artifact.** Every redesigned screen for an institution admin, a supervisor, a trainee and the hire variant. They are drawn with the real tokens: copy the values from `web/src/foundation/ui/tokens.css`, use the assess skin, and the hire skin for the hire boards. Every board lists the inventory items it carries, so the parity check can be seen. A previous canvas is never overwritten: a new artifact goes up each time.
3. **The build, in phases**, after the boards are approved (see Build phases).
4. **The product guide, corrected and republished, with a plain-language chapter covering every institution flow.** Process from `docs/guides/README.md`:
   - `Artifact read` the URL first;
   - edit the "Running exams as a school" and "Employers and partners" chapters, "What is still rough" and the header count and commit;
   - `make product-guide`;
   - republish to the same URL with no icon.
   Once the build ships, it is updated again to describe the new screens.

## Redesign

### 1. One model, five nouns on screen
- **Exam** = the catalogue exam + its marking scheme version + the org programme. The "Available for scheduling" switch maps to programme `active`.
- **Station**. **Station template** is shown as "Station layout (optional)".
- **Sitting**, called "Assessment" for hire.
- **Circuit**: "one run of stations, with a supervisor in charge".

Other wording:
- **Supervisor** replaces "Lead". An info line says supervisors are the examiners.
- **Year group (cohort)** and **Group** are two clearly labelled things.
- **Mode** becomes "Formal exam: marked, signed off, released" or "Training: feedback only". This removes the clash with "Exam".
- Every noun comes from `domains/assess/vocabulary.ts` and `useAssessWords`, with hire variants, so no screen hard-codes "trainee" (fixes the hire leaks).

### 2. Navigation (`surfaces/assess/surface.ts`, `surfaces/hire/surface.ts`), with sections, ordered by job
- **Home**
- **Run:** Sittings, Now running, Results
- **Organise:**
  - People. Tabs: Trainees, Staff, Groups and year groups, Exam access, History. This merges `/team` into People, and `/team` still resolves.
  - Exams. Tabs: Exams, Stations, Marking schemes, Station layouts, Programmes. This is today's Build; the Programmes tab stays as the advanced list.
- **Insight:** Reporting
- Settings

The duplicate Stations and Programmes entries go. Their screens stay as tabs and every old URL still works. Hire gets the same structure in its own words, which fixes Programmes being unreachable on hire. Supervisors see Home, Sittings, Now running, Results, People (read only) and Reporting. Trainee navigation does not change. `surfaces/registry.test.ts` constraints are kept.

### 3. Home (`dashboard/OrgDashboard.tsx`, `dashboard/support.ts`)
**Until setup is complete, a setup assistant.** Five steps, shown one at a time in the old B2B style, with "Step N of 5" and "Continue setup":
1. Set up an exam (adopt one from OSCE Guide, or create your own).
2. Add stations.
3. Add trainees.
4. Invite a supervisor. Optional, and can be skipped.
5. Schedule your first sitting.

The steps are derived from the flags the dashboard api already returns. Each step shows to whoever can do it, not only to `author_content`. The hidden primary button is replaced by a disabled one with its reason.

**Afterwards, "Today":**
- running now (`LiveNow`);
- "Needs your attention": decisions waiting, ready to release, and stations to review (supervisor);
- upcoming sittings;
- counts.

### 4. Exams hub (`capabilities/authoring/*`, `domains/assess/programmes/*`)
- **Exam list.** Each exam shows a status: Draft, "Needs a marking scheme", "Ready to schedule" or "Not available". The status comes from exam publish state + rubric + programme status.
- **"New exam" sheet (wizard):**
  1. Name and code.
  2. Marking scheme: pick, copy from OSCE Guide, or write new (opens the existing rubric builder and returns here).
  3. Timings and settings (the existing `ExamFields` and `ExamSettingsFields`).
  4. Publish. The screens call create exam, then publish, then create programme, then PATCH it `active`. If a step fails, the admin sees a resumable state that names the step.
- **Adopt from OSCE Guide.** One click (the import already produces an active programme).
- **Exam detail:** its marking scheme and version, its stations (the filtered `StationsTable`), its station layouts, the "Available for scheduling" switch (activate, retire or reactivate), its sittings, and Retire or Delete.
- **New station sheet,** with the exam preselected. Five ways in: from a layout (yours or OSCE Guide's), import a PDF or Word file, generate with AI from a brief, or blank. Every authoring feature in inventory items 1.16-1.22 is kept: builder tabs, trial mark, draft instructions, preview, versions, photos, the reading brief, and "Copy to my organisation".

### 5. "Schedule a sitting" wizard
Replaces the `NewSitting` → `SittingDetail` → `NewCircuit` hop. The steps are locked in order, with a step strip and a help panel on each step:
1. **Basics.** Name, exam (only "Ready to schedule" ones, plus an inline "Set up an exam" link), mode with what it means, date, year group.
2. **Stations.** That exam's published stations. Reorder them, cap at 12 for a formal exam, and link to "Add stations" when there are none.
3. **Candidates.** People, groups and year groups:
   - a person who has not signed in shows an inline reason and a "Resend invitation" action;
   - for training, a live counter reads "N trainees for M stations: they must match".
4. **Timing and breaks.** The existing `TimingFields`, with per-break lengths.
5. **Supervisor.** One for all circuits, or one per candidate.
6. **Review and create.** It shows "N candidates × M stations → K circuits", then calls create sitting, then `circuits/bulk` (formal) or `circuits` (training). If the circuits fail after the sitting is created, the admin lands on the sitting with the error and a retry.

The existing `NewCircuit` and `EditCircuit` stay for "Add a circuit" and "Edit" on an existing sitting. Both are rebuilt from the same step components. The disabled submit always says why.

### 6. Sitting page (`SittingDetail.tsx`)
- A header with status and **one** primary action from `sittingSteps.ts`. The duplicate "Add a circuit" goes.
- Sections: Circuits (cards with supervisor and status), Candidates, Results summary.
- Edit gains the year group field (the api supports it).
- Kept: cancel, delete circuit, set a date, open the console, open results.

### 7. People (`roster/*`, `team/*`, `PeopleTabs.tsx`)
- One page with one "Add people" sheet. The sheet asks whether you are adding trainees or staff, then: one person, or a spreadsheet.
- One label throughout: "Add trainee" or "Invite staff".
- The temporary password is explained as "for people who can't receive email".
- The invitation state is explained where it blocks scheduling.
- The bulk bar's "Move to group…" is correctly labelled "Move to year group". Groups get their own action.
- Team bulk revoke is added, through the existing `memberships/bulk/revoke` route.
- Every row action and CSV feature is kept (inventory 1.12-1.13).

### 8. Results and review
- The Results index leads with "Needs your attention".
- The sitting results page and `SlotReview` keep every control.
- The supervisor gets "Stations to review" on Home, built from the existing reads (`SupervisorCircuits` and `LiveMarkingSidebar`).
- "Publish circuit feedback" is explained as the step that finalises.

### 9. Everywhere
- Every empty state links to the fix:
  - `TraineePicker.tsx:61`
  - `capabilities/stations/LibraryBrowse.tsx:66`
  - `Sittings.tsx:165`
  - `ResultsIndex.tsx:112`
  - `reporting/Reporting.tsx`
- Every disabled primary button gives its reason inline.
- A "?" help panel on each page, the pattern from `RunnerHelpPanel`.
- One primary action per screen (`DESIGN.md`, layout principle 1).

### 10. Settings
- New tab "Invoices" (org admin): list, detail and PO number, through the existing `/orgs/{slug}/invoices*` routes. Owner: `access-owner`. Money, so the user reviews it.
- The `NewOrganisation.tsx:143` copy that promises purposes "later in Settings" is corrected.

## Feature parity checklist
The inventory from the sweep goes into the doc as a numbered checklist (sections 0-3: nav, routes 1.1-1.33, api with no screen, gotchas). Each item says where it lives in the new design. Not-yet-mounted things stay as they are, for example `OrgDiscussion` and org practice-access. The checklist also covers:
- live streams: `LiveNow`, `LiveBoard`, the console, `me/sittings`;
- exports: results CSV, result PDF, readout, transcript download;
- the `AdminsOnly` guards, the release confirm, and transcript access for the lead only.

## Build phases (after the boards are signed off)
Each phase goes through `build-feature` with its owner:
- the owner's verify skill, then the web `verify` skill (a browser run against a seeded org: `node scripts/seed-demo-org.mjs`);
- `npm run ci` and `npm run e2e:assess`, plus the hire specs (the hire and partner e2e specs and `roles/role-matrix.spec.ts`);
- `reviewer` + `quality-reviewer`;
- tick the parity checklist items it touches.

| Phase | Scope | Owner |
|---|---|---|
| 0 | Baseline: screenshot every institution screen per role; record that `docs/CORE-JOURNEYS.md` ASSESS-1..6 and HIRE-1..2 pass | `institution-owner` |
| 1 | Vocabulary, nav sections, Home setup assistant, linked empty states, reasons on disabled buttons | `web-foundation-owner` (nav and shell), `institution-owner` |
| 2 | Exams hub, New exam wizard, adopt, exam detail, New station sheet | `content-owner`, `marking-owner` (schemes), `institution-owner` (programmes) |
| 3 | Schedule-a-sitting wizard, sitting page, cohort edit | `institution-owner` |
| 4 | People merge, Add people sheet, team bulk revoke | `institution-owner`, `access-owner` (invitations) |
| 5 | Results "Needs your attention", supervisor review queue | `marking-owner`, `institution-owner` |
| 6 | Invoices tab (money, the user reviews it) | `access-owner` |
| 7 | Docs: update CORE-JOURNEYS steps; add and close EXPERIENCE-GAPS rows; republish the product guide for the new screens | `institution-owner` |

Code that will change, representatively:
- `web/src/surfaces/{assess,hire}/surface.ts`
- `web/src/domains/assess/{dashboard,roster,team,results,programmes}/*`
- `web/src/domains/assess/{NewSitting,SittingDetail,CircuitBuilder,TraineePicker,vocabulary}.ts(x)`
- `web/src/capabilities/authoring/{Authoring.tsx,sections/*,stations/CreateStationScreen.tsx}`
- `web/src/capabilities/stations/LibraryBrowse.tsx`
- `web/e2e/assess/*`

Code to reuse:
- `StepGuide`, `B2CSegmentedTabs`, `B2CHero`, `B2CGroupedSection`, `QuietCard`, `ConfirmModal`, `Modal`, `EmptyState`
- `CircuitBuilder` panels, `TimingFields`, `TraineePicker`, `StationLibrary`
- `ExamFields`, `ExamSettingsFields`, `RubricBuilder`, `ProgrammesSection`, `PlatformExams`, `BulkImportDialog`, `BulkInviteDialog`
- `sittingSteps.ts`, `dashboard/support.ts`

## Order for this session after approval
1. Create the Claude Doc skeleton, fill it, and send the link.
2. Correct the product guide and republish it:
   - `Artifact read`, edit `docs/guides/how-osce-guide-works.html`, `make product-guide`, publish.
   - This is a docs file only, left uncommitted.
3. Build the design boards artifact, using the `artifact-design` skill and the real tokens, then send it for sign-off.
4. Stop. Phase 0 and later start when the user approves the boards.

Save memories:
- for the institution UI overhaul, no feature removal and keep `DESIGN.md`'s language;
- exam, programme and scheme are shown as one "Exam".

## Verification
- **Doc:** every `path:line` was opened. Unconfirmed items are labelled "unverified". The gap rows are checked against `EXPERIENCE-GAPS.md`.
- **Guide:** `cd api && make product-guide` exits 0, with no "Checked against" warning. Read the published page back after republishing.
- **Boards:** every inventory item appears on a board or has a note saying where it lives. The tokens match `tokens.css`. Check at 390px width.
- **Build phases:** the per-phase gates above. Done means the seeded org was walked in a browser as admin, supervisor, trainee and hire admin, and every parity item that phase touches was ticked.

Also tell the user: one committed fix names its causing commit but has no reviewer eval case. Offer to run `.claude/evals/reviewer/sync_cases.sh --score`.
