# Institution overhaul: audit round 2 (2026-11-05)

Sources: four code audits against all 41 boards, a code-correctness review, and the round-2 browser walk (`verify/RESULTS.md`, "Round 2"). Paths are under `web/src/`. README "Judgement calls" and Ledger items are not repeated.

## Must fix

| # | Item | Where | Owner |
|---|---|---|---|
| M1 | Sitting primary action stuck on "Set a date" for a sitting run without a date; Mark/Decide never show | `domains/assess/sittingSteps.ts:115,147` | institution |
| M2 | "Needs your attention" list counts training and not-yet-run sittings as needing a decision; the nav chip filters them, so list and chip disagree. Two builders for one concept | `domains/assess/results/support.ts:329,347`, `dashboard/support.ts:143,177` | institution |
| M3 | "Recruitment outcome (hire only)" shown on an institution's formal exam (gated on mode, not arm) | `domains/assess/results/Results.tsx`, `CandidateCard.tsx`, `CandidateDecision.tsx` | institution |
| M4 | Internal design note rendered to users on Add/Edit circuit | `domains/assess/CircuitBuilder.tsx:170` | institution |
| M5 | Hire vocabulary leaks (an employer reads sitting/trainee/supervisor/circuit/school): every authoring screen (no `useAssessWords` under `capabilities/authoring`), schedule wizard, Sitting page and actions, Sittings, live board, console add dialog, results, Reporting, trainee sitting/review, People edit, `errorCopy.ts`. Needs `vocabulary.ts` + `useAssessWords.ts` moved to `capabilities/` so authoring may use them | many; see the agents' lists | web-foundation (move), then content, institution |
| M6 | Slot review form keeps withdrawn ratings/notes after "Withdraw draft"; not keyed by slot, so the stepper can carry A's marks to B | `domains/assess/SlotReview.tsx:117-132` | institution (marking reads) |
| M7 | Raw mode word ("exam", "Exam") where boards say "Formal exam"/"Training" | `NewCircuit.tsx:100`, `EditCircuit.tsx`, `sessions/support.ts` `sittingModeLabel`, `dashboard/LiveBoard.tsx` | institution |
| M8 | Hire candidate shown "Keep practising / Self practice" card on their result | `domains/assess/trainee/MyResult.tsx` | institution |

## Should fix

| # | Item | Where | Owner |
|---|---|---|---|
| S1 | Results nav chip refetched on every navigation yet stale after sign-off/release on the same page | `surfaces/useNavBadges.ts:35` | web-foundation |
| S2 | Refusal codes with no copy fall to server English (programme/trainee/circuit): `lead_cannot_run`, `marking_not_ready`, `programme_not_active`, `exam_rubric_not_ready` (wizard), `not_permitted_in_mode`, `trainee_already_on_circuit`, `station_not_on_circuit`, `review_locked`, `not_slot_reviewer`, `circuit_review_finalized`, `decision_outside_exam`, `candidate_did_not_sit`, `too_many_trainees`; copy must be vocabulary-aware | `domains/assess/errorCopy.ts` | institution |
| S3 | Partner admin not appointed reporter sees raw `not_a_partner_reporter`; no copy for `unknown_partner`, `invalid_date_range` | `domains/partner/*`, `capabilities/attribution-dashboard/LoadFailure.tsx` | institution |
| S4 | Roster bulk action: a later 500-id chunk failing hides that earlier chunks succeeded; generic message | `domains/assess/roster/TraineesPanel.tsx:161` | institution |
| S5 | "N not joined" row not refreshed after add/import/resend | `domains/assess/people/People.tsx:71,181` | institution |
| S6 | Circuit builder: training trainees == stations rule missing (vague `invalid_circuit`); "at most 1 candidates"; missing "N of M selected. A formal exam circuit is one candidate's sitting…"; search label uses exam code, board uses name | `domains/assess/CircuitBuilder.tsx:209,238` | institution |
| S7 | Sittings "Next up" can pick a cancelled/reviewed sitting | `domains/assess/Sittings.tsx:38` | institution |
| S8 | Schedule wizard: "Set up an exam" goes to Programmes, not New exam; retry notice `onDone` doesn't reload the step guide | `NewSitting.tsx`, `PendingCircuitsNotice.tsx:35` | institution |
| S9 | Copy vs board: count tile "Supervisors" (board "Staff"); running chip "In progress" (board "Running"); People edit "Cohort" + tooltip offering email change; duplicated supervisor read-only line; "is now supervisor here"; "N more circuits" off by one; Reporting "1 sittings"; trainee review subtitle missing; trainee row "Feedback ready" badge; Self practice eyebrow, exam chip, "Practise" button; Trainee home "Practice sessions" row | `dashboard/OrgDashboard.tsx`, `Sittings.tsx`, `roster/TraineeEditDialog.tsx`, `TraineeRowActions.tsx:58`, `people/People.tsx`, `team/InvitePanel.tsx`, `SittingDetail.tsx`, `reporting/Reporting.tsx`, `trainee/*` | institution |
| S10 | Authoring copy: Create station back link "New station" + eyebrow "Exams › Stations"; "Station layouts" not "Station templates"; "Scoring (feedback layouts)"; layout save failure has no "Try again" | `capabilities/authoring/stations/CreateStationScreen.tsx`, `templates/StationTemplate{New,Edit}Screen.tsx`, `structure/b2b/lib/stations/blockTypeLabels.ts:22` | content |
| S11 | Marking scheme: "Shown/Hidden" chips and "[Add a field]" (api data since 6faaf8cb), "Weight 1 [Edit]" on area rows, "Tone" label | `capabilities/authoring/rubrics/DisplayPanel.tsx:77-100`, `RubricBuilder.tsx:141` | marking |

## API-limited (not built; needs your decision)

- Durable resume of a failed schedule (pending circuits live only in sessionStorage) and an idempotency key on create-sitting (a lost response then Create makes two sittings): both need api support.
- Edit circuit "Breaks" panel (per-circuit breaks after station N): the api has an exam-level break only.
- Supervisor home "8 trainees" on the next circuit: needs a candidate count on `/supervisor/circuits` rows unless it is already there (owner to confirm).
- In-room "You / Microphone on" tile and "Speaking" state for the trainee: attempt-engine/LiveKit work, out of this round.
- S1 Results nav chip goes stale after sign-off/release on the same page: no `org.results_changed` me-event exists. Options: add the api event (recommended) or a web-only refresh signal.
- Marking scheme "[Add a field]": the api has five fixed feedback-display keys and all five are already listed, so there is nothing to add.
- Marking scheme "Weight N [Edit]": rubric areas carry no weight; `scoring.py` weights areas equally. Needs an api field and a scoring change.
- Hire word for "circuit": no board defines one, so employers read "circuit". If you want another word, about 5 titles need templating.

- Console slots carry no "a station was sat" field: `attempt_id` is null when the only attempt failed, so that station reads "0 of 1 stations sat". Needs a field such as `slots_with_attempts` (`attempts/service_reads.py:230`) on the console slot. The web now uses one rule (`stationWasSat`) in the console and the sitting page.

## Round 2 browser walk (see verify/RESULTS.md)

Fixed on the branch after the walk: running-circuit note on supervisor home, "N of M stations sat" counts real attempts, import dialogs show only "Done" after an import. Not reproduced: supervisor circuit-run 403s. e2e: ROLES-1 and SWITCH-1/2/3 pass on a production build (dev-server timeouts); board-home pixel and style tests are not caused by the branch (spec exists only untracked in main, and main's uncommitted SetupAssistant/OrgDashboard edits likely feed it); ASSESS-2/3 need LiveKit.

## Your own read (auth, money)

- Sign-in family: boards say `/sign-in` and `/invitations/accept`; the app has `/login` and `/accept-invitation`. No "You are in / Go to my training" screen after accepting an invitation (it signs in and goes to `/app`). Register organisation lives at `/register/organisation` and is signed-out only; the board says `/organisations/new`, open to anyone signed in. SSO callback and not-set-up copy differ from the board.
- Invoices: copy matches. Behaviour: `manage_team` gate; PO editable only while issued; empty/over-64 rejected; reload drops back to the list.
- Partner fee note: when a fee is set, the title and text differ from the board ("Estimated fee (guide only)" plus the server disclaimer).
- Hire result: the board says the recruitment outcome is never shown to the candidate; the web shows what the api returns. Confirm the api withholds it.

## Fully matched

NewStation, ImportStation, BuildGuide (dev guide), Results (date format aside), Settings, Invoices (copy), HireHome and SupervisorHome (low items aside).

## Low (accepted unless an owner touches the file)

Date formats via `toLocale*`; "Reconnecting…" ellipsis; Download vs Export CSV; Withheld hint wording; InterventionsLog order; consumer "Create account" footer on sign-in; non-.csv drop silently rejected; group members count of loaded page; extra statuses "Accepted, not a member"/"Anonymised".
