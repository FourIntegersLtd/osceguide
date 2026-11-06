# Marking scheme builder: parity with the approved board

Board: `project/SchemeBuilder.dc.html` (artifact 9FqgBbWctqPLRsVo27KUgD), 38 states.
Walked on 2026-11-06 against the local stack with `web/.verify/scheme-walk.mjs` (plus `scheme-raw.mjs` for state 37),
signed in as the walkthrough user. Screenshots: `scheme-parity/NN.jpg` (NN is the script's step, mapped below);
text per step: `scheme-parity/walk-log.json`.

Re-run in full on 2026-11-06 after the review fixes: all 42 script steps ran, exit 0. The only logged problems are the two deliberate ones (the 502 forced at step 29, the 409 conflict at step 32). Steps 32 and 33 had timed out after the Apply/Discard rule; the cause was confirmed: step 24 left a broken JSON edit unapplied, which keeps Save off. The script now clicks "Discard edits" after step 24, and 32 and 33 pass. State 25 to 29 previews no longer show the "formative training only" line.

Result: 38 of 38 states match on structure and copy after fixes. Two points differ in detail and are listed under Remaining.

| # | Board state | Script step | Result | Fixed? |
|---|---|---|---|---|
| 1 | The tabs, in order | 1 | Matches: 7 tabs, step footer "Step 1 of 6: Domains", Next: Scale | Yes (footer labels Back: X / Next: Y) |
| 2 | Domains: the outline | 2 | Matches: caret, competency count chip, Details and menu per row, Add competency row, first domain open | Yes (collapse caret, Details button, Add competency row) |
| 3 | Details of a domain | 3 | Matches: panel under the outline with kind label and Done | Yes (panel moved out of the row) |
| 4 | Details of a competency | 4 | Matches: "Competency in X" | Yes |
| 5 | The Add menu | 5 | Matches: Domain, Competency, Notes, Scale, Pass rule, Feedback | No change needed |
| 6 | A competency was added | 6 | Matches | No change needed |
| 7 | Reorder and the menu | 7 | Matches: Move up, Move down, Duplicate, Delete | No change needed |
| 8 | Deleting asks first | 8 | Matches: names the item and what goes with it | Yes (copy) |
| 9 | Notes blocks | 9 | Matches: notes panel lists feedback items | Yes |
| 10 | A Custom row | 10 | Matches: "Custom field / Kept as it is" row | Yes |
| 11 | Scale: pick a preset | 11 | Matches. A confirm appears only when level descriptions exist (board shows it for that case; in a blank scheme the preset applies at once) | Yes (copy, nearest-level rule move) |
| 12 | Scale: levels and points | 12 | Matches | No change needed |
| 13 | Scale: a number range | 13 | Matches | No change needed |
| 14 | A problem blocks publishing | 14 | Matches: badge on the tab, blocked banner with See problems | Yes (banner copy) |
| 15 | Pass rule: domains | 15 | Matches | No change needed |
| 16 | Pass rule: a score instead | 16 | Matches | No change needed |
| 17 | Pass rule: the station | 17 | Matches, including "Set a domain pass line first" | No change needed |
| 18 | Feedback: what the marker writes | 18 | Matches | No change needed |
| 19 | Feedback: what the candidate sees | 19 | Matches (Shown/Hidden switches) | Yes |
| 20 | Advanced: marking instructions (drafting) | 20 | Matches. The Draft button waits on the AI model, which the local stack answers slowly | No change needed |
| 21 | Advanced: drafted | 21 | Matches: "Drafted instructions for 1 place. Read them before you save." | No change needed |
| 22 | Advanced: no instructions | 22 | Matches: blocker names the Advanced tab | No change needed |
| 23 | Advanced: pacing and examiner layout | 23 | Matches | No change needed |
| 24 | Advanced: scheme as JSON (broken edit) | 24 | Matches: refused edit keeps the last good scheme | No change needed |
| 25 | Preview: dashboard | 25 | Matches | No change needed |
| 26 | Trial mark: choose | 26 | Matches | No change needed |
| 27 | Trial mark: running | 27 | Matches: "Marking... Stop, 0 s, 1 turn" | No change needed |
| 28 | Trial mark: result | 28 | Matches: marked by, not saved | No change needed |
| 29 | Trial mark: failed | 29 | Matches: Alert in the trial panel, trial can be run again. The text in the walk is the client's dev hint because the walk simulates the failure with a bare 502 | No change needed |
| 30 | Versions | 30 | Differs in detail: per-row "New draft from this" is one button for the current/latest version (see Remaining). "Back to the steps: Domains" and "outside the steps" match | Partly |
| 31 | Archiving a version | 31, 38 | Matches: modal names exams that use it and what archived means | Yes |
| 32 | Save refused | 32 | Matches: "saved somewhere else", Reload latest | Yes (conflict Alert) |
| 33 | Publish | 33 | Matches: confirm names the exams that keep the old version | Yes |
| 34 | Published | 34 | Matches: banner with Open the exam | Yes |
| 35 | Leaving with unsaved changes | 35 | Matches | Yes (message) |
| 36 | A published version, read only | 36, 37 | Matches: read-only banner, New draft from version N, draft-exists modal | Yes |
| 37 | A scheme the builder cannot show | 39-40 (`scheme-raw.mjs`) | Matches: Domains alert plus "Scale, Pass rule and Feedback are hidden too"; the three tabs show the empty-tab Alert with Open the JSON | Yes |
| 38 | On a phone | 41, 42 | Matches: Details open as a bottom sheet titled by kind, footer stacked | Yes (sheet title) |

## Remaining

1. State 30: "New draft from this" per older version needs the api to copy a chosen version; today the api copies the latest. The builder starts the draft from the version you are on and says so; not changed (api contract, out of scope).
2. Switching a scheme that carries `advanced.tones` to a labels scale leaves the tones in place and the api then blocks publishing ("remove tones"). Found by the walk; the builder shows the problem on the Advanced tab but does not clear the tones. Left as is: a decision for marking-owner.

## The other 42 boards

Checked by file and route in `web/src`, not by walking each screen.

Built: Exams, NewExam (`authoring/exams/new`), ExamSettings, ExamDetail, Sittings, ScheduleSitting, Sitting, EditCircuit, Circuits console, LiveBoard, Results and SittingResults, SlotReview, Reporting, Settings, Invoices, SetupAssistant, SupervisorCircuits, Programmes, People (team, trainees), RegisterOrg (`register/organisation`), AcceptInvite (`accept-invitation`), the Exam access panel (`roster/AccessPanel.tsx`), Stations, Station templates, Marking schemes.

Not found by name: HireHome (`surfaces/hire` has a manifest only), AdoptExam, Today (the workspace home may be its equivalent). Not built here: each needs an api flow or a product decision (adopting an exam from the catalogue, a hire landing page) that is not in the marking-scheme area, so they are listed, not built.
