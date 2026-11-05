# Inventory (Phase 0, baseline of today's app)

Assembled from five code-reading passes (shells/hire/partner, sittings/live, results/trainee/settings, people/programmes, authoring). Source: code under web/src; entries marked [code] were read from code, [browser] were also confirmed in a browser. See baseline/RESULTS.md for e2e and journeys.

<!-- parts/1-sittings-live.md -->
# Baseline part 1: sittings, circuits and live screens

Read-only inventory. All paths are relative to `web/src/`. Format: `"exact string"` file:line.
Hire is a workspace whose surface is `hire` and borrows these screens (`surfaces/assess/screens.tsx (assessScreens export, end of file)`, `assessScreens`). Noun-driven strings come from `useAssessWords` (`domains/assess/useAssessWords.ts`, `vocabulary.ts`).

## 0. Shared vocabulary and shared component defaults

Words (`domains/assess/vocabulary.ts:16-47`), institution / hire:

| key | institution | hire |
|---|---|---|
| sitting / sittings | "sitting" / "sittings" | "assessment" / "assessments" |
| Sitting / Sittings | "Sitting" / "Sittings" | "Assessment" / "Assessments" |
| trainee / trainees | "trainee" / "trainees" | "candidate" / "candidates" |
| Trainee / Trainees | "Trainee" / "Trainees" | "Candidate" / "Candidates" |
| People | "People" | "Candidates" |
| scheduleSitting | "Schedule a sitting" | "Schedule an assessment" |
| addPeople | "Add people" | "Add candidates" |

Anything below that is a literal not built from `w.*` is the same in both workspaces (note: many literals say "sitting", "trainee", "candidate" even in hire; those are flagged "LITERAL" so Phase work can decide).

Shared component defaults (apply wherever a screen uses them):
- `AsyncBoundary` loading: centred `<Spinner size="lg" />` (no text). Error: Alert title "That did not load", body = `error.message` or "Something went wrong.", button "Try again" (`foundation/ui/AsyncBoundary.tsx:57-95`).
- `Table` with `more`: footer button "Load more" / "Loading…" / "Try again"; error line "Could not load more: {message}" (`foundation/table/Table.tsx:319-331`).
- `ConfirmModal` defaults: title "Confirm", confirm "Confirm", cancel "Cancel" (`foundation/ui/ConfirmModal.tsx:~42-50`).
- `B2CPageHeader` back link default label "Back" (`foundation/ui/B2CPageHeader.tsx:37`).

## Route map (web/src/app/app/[workspace]/)

| Route | Screen key | Component (surfaces/assess/screens.tsx) | Gate |
|---|---|---|---|
| `/dashboard` (`dashboard/page.tsx`) | dashboard | `AssessDashboard` :66 | `run_circuits` else `TraineeHome` (:69) |
| `/sittings` (`sittings/page.tsx`, metadata title "Sittings") | sittings | `AssessSittings` :73 | none on view; schedule button gated `schedule_sittings` |
| `/sittings/new` (title "New sitting") | newSitting | `AssessNewSitting` :81 | `AdminsOnly` = `schedule_sittings` (:53) |
| `/sittings/[sittingId]` | sittingDetail | `AssessSittingDetail` :77 | none on view; actions gated per control |
| `/sittings/[sittingId]/circuits/new` (title "New circuit") | newCircuit | `AssessNewCircuit` :89 | `AdminsOnly` `schedule_sittings` |
| `/sittings/[sittingId]/results` (title "Results") | sittingResults | OUT OF SCOPE (marking-owner) | |
| `/circuits/[circuitId]` | circuitConsole | `AssessCircuitRunner` :101 | none in route; controls gated inside (`run_circuits`) |
| `/circuits/[circuitId]/edit` (title "Edit circuit") | circuitEdit | `AssessCircuitEdit` :105 | `AdminsOnly` `schedule_sittings` |
| `/live` | live | `AssessLiveBoard` :97 | none in route (api gates) |

`AdminsOnly` fallback (`surfaces/assess/screens.tsx:53`): EmptyState title "Administrators only", description "Ask an administrator to make this change."

## Sittings list (`/sittings`)
File `domains/assess/Sittings.tsx` + `SittingFilterBar.tsx`. Seen by any org member whose route loads; schedule button needs `schedule_sittings` (:127).

- Heading: `w.Sittings` -> "Sittings" / "Assessments" (:125). Browser title (route): "Sittings".
### Buttons
- Page action `w.scheduleSitting` -> "Schedule a sitting" / "Schedule an assessment" (:129), links `/sittings/new`, only if `schedule_sittings`.
- Next-up hero action: `Open {w.sitting}` -> "Open sitting" / "Open assessment" (:185), links `/sittings/{id}`.
- Table footer "Load more" / "Loading…" / "Try again" (Table.tsx:331).
- "Clear filters" (SittingFilterBar.tsx:52), shown only when any filter active.
### Tabs and filters
- Mode segmented tabs, aria-label "Filter by mode" (:143): "All", "Exam", "Training" (:148-150). LITERAL.
- Search box placeholder `Search by {w.sitting} name` -> "Search by sitting name" / "Search by assessment name" (:156); aria-label `Search {w.sittings}` (:157). 300 ms debounce (:114).
- Filter group aria-label "Filter sittings" (SittingFilterBar.tsx:21) LITERAL.
- Select "Status" (:23): options "Any status", then humanised "scheduled", "in_progress", "completed", "cancelled" -> "Scheduled", "In progress", "Completed", "Cancelled" (:28-33, STATUSES :7).
- Select "Programme" (:36): "Any programme", then each programme's `exam_name` (:41-46).
- Date inputs "From", "To" (:48-49).
### Table columns (:52-94)
- `w.Sitting` (name, link to detail), "Mode" (capitalised raw `sitting.mode`), "Programme" (`programme_name` or empty), "Scheduled for" (locale date or "Not scheduled"), "Status" (Badge, humanised status; success variant when running).
### Next-up hero (:173-197)
- Eyebrow "Next up" (:175); title `{name} is running now` when running else name (:177); body = programme name · locale datetime · `{n} candidate`/`candidates` (:192, LITERAL "candidate(s)" even in hire).
- Scope note when more pages: `Next up covers the {loaded} sittings loaded so far. Load more to include the rest.` (support.ts:206, LITERAL "sittings").
### States
- Loading: AsyncBoundary default spinner. Error: "That did not load" + "Try again".
- Empty (no rows and no filter): title `No {w.sittings} yet` -> "No sittings yet" / "No assessments yet" (:165); description: with schedule perm "Schedule your first one to get started."; without: `An administrator schedules {w.sittings}; they will appear here.` (support.ts:210-214).
- Empty with filters: table empty title `No {w.sittings} match.` (:207).

## New sitting (`/sittings/new`)
File `domains/assess/NewSitting.tsx` + `SittingFields.tsx`. Gate: `schedule_sittings` (AdminsOnly). Route title "New sitting".

- Page header: title `w.scheduleSitting` ("Schedule a sitting" / "Schedule an assessment") (:31); back link label `w.Sittings` -> `/sittings` (:30); subtitle `A training {w.sitting} rotates a group through stations; an exam {w.sitting} is one {w.trainee}, marked, signed off and released. Add circuits next.` (:32).
- Panel title "Details" (:120).
### Fields
- Input "Name", required, placeholder "March mock OSCE" (:125-129).
- Mode fieldset legend "Mode" (SittingFields.tsx:34); two toggle buttons: "Exam" / "Marked, signed off and released"; "Training" / "Feedback straight to the trainee" (:38-39). Default Training. Hint under: exam "One candidate takes every station, up to twelve. You cannot add trainees once it has started."; training "Each trainee is paired with one station, and they rotate." (:62-63; LITERAL "candidate", "trainees").
- Select "Programme" (:92); options `{exam_name} ({exam_code})`; only active programmes; helper "Marking and feedback follow the published marking scheme for {exam_name}, so there is nothing else to choose." (:103).
- Select "Cohort (optional)" (:122) only when cohorts exist; options "No cohort" + cohort names.
- Datetime "Scheduled for", hint "Leave empty to schedule it later." (:142, :134).
### Buttons
- "Cancel" (link to `/sittings`) (:146). Submit `Create {w.sitting}` -> "Create sitting" / "Create assessment" (:149), spinner label "Creating" while busy; disabled when busy, name empty or no programme.
### States
- Loading/error: AsyncBoundary defaults.
- No active programme: Alert (warning) title "Activate a programme first" (drafts exist) or "Add a programme first" (:106). Body: `{drafts} is|are still a draft. Activate it in Programmes, then come back here.` (:109) or `Every {w.sitting} belongs to a programme, and that programme’s exam needs a published marking scheme. Add a programme and activate it, then come back here.` (:110). Button "Go to programmes" (:113).
- Submit error: Alert (danger) with `errorMessage(error)` (:122).
- On success: router push to `/sittings/{id}` (no toast).

## Sitting detail (`/sittings/[sittingId]`)
Files `domains/assess/SittingDetail.tsx`, `SittingActions.tsx`, `SittingEditForm.tsx`, `sittingSteps.ts`. Anyone may view; `manage = can(schedule_sittings) && status !== "cancelled"` (:55) gates Edit, Cancel, Add a circuit, Delete, Set a date; `sign_off_results` changes step wording (:126).

- Header: back link `w.Sittings` -> `/sittings` (:80); eyebrow = `sittingModeLabel` "Training"/"Exam" (:81); title = sitting name (:82); subtitle = short datetime or "No date set" (:84).
### Buttons (header, :86-120)
- Status Badge: humanised status (:89), success dot when running.
- "Edit" (:93), manage only; opens SittingEditForm dialog.
- "Cancel sitting" (:98), manage and no circuit started; opens cancel confirm. LITERAL "sitting" (no `w`).
- "Results" (link `/sittings/{id}/results`) (:107), always.
- "Add a circuit" (link `/sittings/{id}/circuits/new`) (:116), manage only.
### Next-step guide (StepGuide, :123, :218-249; wording `sittingSteps.ts`)
- Steps rail labels: "Schedule", "Circuits", "Run", "Mark", then (exam only) "Decide", "Release" (:113-131). Training stops at Mark (:127).
- Step notes: "Date set" / "No date"; "None yet" / `{n} circuit(s)` / `{n} candidate(s) assigned` / "Candidates sat"; Run: "Circuit ended, nobody sat", "All finished", "Nobody has sat yet", `{n} of {m} stations sat`, `{f} of {c} finished`, "Not started"; Mark/Decide/Release: "Not started" or `{n} of {m} marked|decided|released` (`results/support.ts:321`).
- Next line + action button (shown only if `actionable`):
  - schedule: "Set a date for this sitting." -> button "Set a date" (SittingDetail:60) opens edit form.
  - circuits: "Add a circuit so candidates can take this sitting." -> "Add a circuit" (:65).
  - run: "The circuit ended and nobody sat. Open it to see what happened, or add another circuit." / "A circuit is running. Follow it from its console." / "Start the circuit from its console when everyone is ready." -> "Open the console" (:70) to `/circuits/{id}` (circuit chosen by `circuitToOpen`).
  - mark: "Marking is not finished. Review each station on the results page." -> "Open results" (:254).
  - decide: "Record and sign off each candidate's outcome." (sign_off_results) / "Waiting for an administrator to record and sign off each outcome." (no button) -> "Open results".
  - release: "{n} result(s) signed off and not yet released." / "{n} result(s) signed off, waiting for an administrator to release them." / "Sign off the remaining outcomes, then release them." / "Waiting for an administrator to sign off and release the results." -> "Open results".
  - done: "Every station has been marked." (training) / "Every result has been released.".
  - Cancelled sitting: no guide (:229).
### Circuits section
- None: B2CHero eyebrow "Circuits", title "No circuits yet", body "Add at least one circuit so candidates can take this sitting." (:140-141). LITERAL "candidates".
- List eyebrow "Circuits" (:144). Each row (link to `/circuits/{id}`): title circuit name; meta = state · `{n} {w.trainee|w.trainees}` · `Led by {supervisor_name ?? "another supervisor"}` or "No supervisor assigned" (:154-160). State: "Finished" / `Running since {time}` / "Not started" (:212-214).
- Row trailing badge: "Your circuit" (own, :163) or "Running" (:165). Own circuits sorted first (:200).
### Row actions
- "Delete" (:176) per circuit, manage only and circuit never started.
### Dialogs
- Cancel sitting confirm (SittingActions.tsx:57-69): title "Cancel this sitting?", body "Nobody can sit it once it is cancelled. It stays in the list, marked cancelled.", confirm "Cancel sitting", cancel "Keep it", danger.
- Delete circuit confirm (:45-55): title `Delete {circuit.name}?`, body "Its candidates and stations come off this sitting. Nothing has been sat on it yet.", confirm "Delete circuit", cancel "Cancel" (default), danger.
- Refusals shown in dialog: sitting_locked "A circuit on this sitting has started, so it cannot be cancelled. End its circuits instead." (:75); circuit_locked "This circuit has started, so it holds what was sat and cannot be deleted." (:78); else `assessErrorMessage` (`errorCopy.ts`).
- Edit this sitting dialog (`SittingEditForm.tsx:86-148`): title "Edit this sitting"; lead "Only what you change is written. The name and the date can move for the life of the record; what the sitting examines cannot once anybody has been examined against it."; buttons "Cancel", "Save sitting" / "Saving…" (disabled when busy, empty name or no change).
  - Warnings (Alert): begun: "A circuit in this sitting has already started, so its type and programme can no longer change. You can still rename it or change its date. To examine something different, rebuild the circuits or schedule a new sitting." (:101); has circuits: `This sitting already has {n} circuit(s), so its type can no longer change. Those circuits were built for this type.` (:105).
  - Fields: Input "Name" (required); Mode (same as New sitting, disabled when modeFrozen); Programme select (options `programmeChoices`, disabled when assessmentFrozen); "Cohort (optional)" when cohorts exist; "Scheduled for" with hint "When it takes place. Leave this blank to remove the date." (has date) or "Leave empty to schedule it later." (:143-144).
  - Error strings (:160-173): stale_revision "Someone else changed this sitting just now. We have reloaded it: close this and choose Edit again to see their changes."; sitting_locked "This sitting has begun, so what it examines is fixed. Its name and date can still change."; exam_rubric_not_ready / rubric_version_not_published "That programme has no published marking scheme yet. Publish one, or choose another programme."; programme_not_found "That programme is no longer here. Pick another."; else `errorMessage`.
### States
- Loading/error: AsyncBoundary defaults, for the sitting and separately for the report (steps) (:50, :231).
### Toasts
- None (dialogs reload via `state.reload`).

## New circuit (`/sittings/[sittingId]/circuits/new`)
Files `domains/assess/NewCircuit.tsx`, `CircuitBuilder.tsx`, `TraineePicker.tsx`, `TimingFields.tsx`, `capabilities/stations/StationPicker.tsx`. Gate: `schedule_sittings` (AdminsOnly). Route title "New circuit".

- Header: back link = sitting name -> `/sittings/{id}` (NewCircuit:95); title "Add a circuit" (:97); subtitle `{sitting.name} · {sitting.mode}` (raw mode, :98).
- Submit label "Create circuit" (:166); in bulk (exam with more than one candidate) button reads `Create {n} circuits` (CircuitBuilder:211). Exam bulk -> one circuit per candidate via name prefix.
- All of the builder below (shared with Edit circuit) is the same, with `allowManyCandidates` true only here.
### CircuitBuilder (`CircuitBuilder.tsx`)
- Alerts: submit error `assessErrorMessage` (:216); too many candidates (warning) `An exam run takes at most {cap} candidates at a time. Deselect {n}.` (:219; cap 200 bulk / 1 edit, `timing.ts:46-49`); too many stations "An exam circuit takes at most 12 stations." (:225).
- Panel "Details" (:229):
  - Input `Name` (bulk: `Name prefix`), placeholder `Morning circuit` (bulk: `Exam`) (:232-235). Blank name defaults to "Exam" (bulk) or "Circuit" (:166).
  - Select "Lead" (:238): option "Unassigned"; staff (admin/supervisor only) as `{email} ({role})` (:247).
  - Input "Reading (minutes)" (number, min 1 max 30; `TimingFields.tsx:27`); Input "Consultation (minutes)" (number, min 1; :35). Defaults reading 3, consultation 10, break 5 (`timing.ts`).
- Panel "Breaks" (exam mode only; `TimingFields.tsx:73-74`): description "A break goes between two stations, never after the last one. Everyone on the circuit pauses during it."; Input "Default break length (minutes)" (1-60); when fewer than 2 stations "Add a second station before adding a break." (:89); otherwise toggle chips `After station {n}` (:111) per gap, and when on a small number input aria-label `Break length after station {n} (minutes)` (:115).
- Panel "Trainees" (TraineePicker): description `{picked} of {total} selected. ` + exam "An exam circuit is one candidate's sitting: they go through every station." / training "Each trainee is paired with one station, then they rotate." (:53-57). LITERAL (not hire-aware).
  - Empty: "Add trainees to your organisation first." (:61).
  - Selects (only when sets exist): label "Add a group" / "Add a cohort", placeholder option `Add a group…` / `Add a cohort…` (:67-81). Status line after pick: `Added {n}.` or `Added {n}. {m} not signed in yet, so they were left out.` (`support.ts:253`); failure `Could not load {label}. Try again.` (:47).
  - Input "Find a trainee" (:98). Chips per trainee (name or email); pressed = picked. Not-signed-in trainees: dashed non-button `{label} · not signed in` with title "They have not signed in yet, so they cannot be put on a circuit." (:126, :123). Chip disabled when exam and full, tooltip "An exam circuit is one candidate's sitting. Deselect the current candidate to pick another." (:139).
- Panel `Stations ({n})` (:283): ordered list `{i}.` + title; icon buttons aria-label `Move {title} up`, `Move {title} down`, `Remove {title}` (:299-321). Then station picker:
  - Search input placeholder "Search stations by name..." aria-label "Search stations by name"; when text typed buttons "Clear" and "Search" (`StationFilters.tsx:29-45`).
  - Each row: station identity, exam-code badge (uppercase), button "Add" (pickLabel, :348) / "Added" when already chosen (`StationPicker.tsx:72`).
  - Empty: title "No stations here yet", description `Published stations for {EXAMCODE} will appear here.` or "Published stations for this exam will appear here." (:47-50). Footer button "Load more stations" (:88).
- Submit button disabled unless stations > 0, picked > 0, within caps, not busy (:361-368); busy shows spinner with the button label.
### States
- Loading/error: AsyncBoundary defaults (NewCircuit:89). Success: router push to `/sittings/{id}` (no toast).

## Edit circuit (`/circuits/[circuitId]/edit`)
File `domains/assess/EditCircuit.tsx` (+ CircuitBuilder as above, without groups/cohorts and capped at 1 exam candidate). Gate `schedule_sittings`. Route title "Edit circuit".

- Header: back link "Circuit" -> `/circuits/{id}` (:99); title "Edit circuit" (:101); subtitle `{sitting.name} · {sitting.mode}` (:102).
- Submit button label "Save changes", or "Rebuild refused" and disabled when locked (:110-111).
- Locked (Alert warning) = `editLockNotice` (`sessions/support.ts:236-255`): circuit_ended "This circuit has finished, so its stations can no longer be changed."; consultation_in_progress "Someone is taking a station right now. Changing the stations would delete that consultation."; feedback_recorded "Feedback has already been given on these stations, so they cannot be changed."; fallback "This circuit cannot be restructured right now.". Plus panel heading "While the circuit is locked", body "Nothing on this form can be saved while the circuit is locked. While it is running, change its timings from the live circuit screen." (:118-123).
- Stale lock (save refused circuit_locked / stale_revision): Alert title "This circuit changed while you were editing", body "Nothing was saved. Reload to see its current state; your changes on this form will be lost.", button "Reload the circuit" (:221-228).
- Prefill: name, stations, picked trainees, lead, timing from the console (:168).
- States: AsyncBoundary defaults. Success: router push to `/circuits/{id}`.
- Errors via `assessErrorMessage` (`errorCopy.ts`): circuit_locked "This circuit has started or has feedback recorded, so its stations can no longer be changed. Reload to see where it is now."; invalid_circuit "This circuit cannot be built as set up. Check the stations, candidates and timings."; others in that table (sitting_not_found, circuit_not_found, programme_required, trainee_* etc.).

## Circuit console / runner (`/circuits/[circuitId]`)
Files `domains/assess/sessions/CircuitRunner.tsx`, `SupervisorControls.tsx`, `OverrideDialog.tsx`, `TurnStrip.tsx`, `StationProgressList.tsx`, `CircuitFeedbackCard.tsx`, `AddTraineesDialog.tsx`, `RunnerStepper.tsx`, `RunnerHelpPanel.tsx`, `SupervisorReadingBrief.tsx`, `ObserverPanel.tsx`, `ObserverVideoGrid.tsx`, `LiveMarkingSidebar.tsx`, `InterventionsLog.tsx`; strings in `sessions/support.ts`, `latecomers.ts`. The route has no client permission gate (the api enforces `run_circuits`); client checks only: `schedule_sittings` for the Edit link (CircuitRunner:100), `sign_off_results` for one sentence (SupervisorControls:70). One screen for training and exam; exam hides TurnStrip and Add trainee (:116, :161, :195). Data is an SSE console frame (`useCircuitRun`), no polling.

- Header: back link = sitting name -> `/sittings/{id}` (:89); title = circuit name (:90); subtitle = `observerSubtitle` + ` · Supervisor: {name|email}` or ` · No supervisor assigned` (:91-93). Subtitle forms (`support.ts:~190-220`): `{candidate} · ` prefix when one trainee; "Ended" / `Ended · {n} of {m} stations sat`; "Not started"; `Station {i} of {n}` · phase; "Between stations"; "Running"; "Paused"; `{n} trainees`.
- Phase labels (`support.ts:20-24`): "Reading time", "Consultation", "Break", fallback "Not running".
### Buttons and links (header, :94-122)
- Help icon button (aria-label = "Running a practice circuit" training / "Observing an examination" exam), opens popover; "Dismiss help" backdrop button (`RunnerHelpPanel.tsx:47,58`).
  - Popover training: title "Running a practice circuit"; intro "The circuit runs itself on the clock you set. You watch it, and step in when something needs a human."; bullets "Start the circuit to open the room; everybody joins from their own screen." / "Reading time and the patient follow the server's clock, not this browser." / "Pause, extend, resend or jump when you need to. Each one asks why, and your answer is saved." (:9-16).
  - Popover exam: title "Observing an examination"; intro "One candidate, every station, on the examination's own clock. You are here to watch it and to mark it."; bullets "Station progress updates as the candidate finishes each one." / "Listening in is subscribe-only: you can hear the consultation and cannot be heard in it." / "Mark a station from its row as soon as it has been sat." (:18-26).
- "Edit" link to `/circuits/{id}/edit`, shown only if `circuit.editable` and `schedule_sittings` (:102).
- Status badges: "Live" / "Reconnecting" (not ended), "Ended" (:110-113); "Paused" (:115).
- "Add trainee" button (:118), training and live only; opens AddTraineesDialog.
### Alerts (circuit.alerts codes, `support.ts:36-46`, :126)
- no_running_attempt "The patient has not joined this station. Resend the patient if this does not clear."
- attempt_failed "This station's consultation failed. Resend the patient, or redo the station once it is safe to."
- voice_fault "The voice service is not answering, so the patient cannot join. The circuit will try again by itself; resend the patient if it does not clear."
- clock_overdue "The clock has run past this phase and the circuit has not moved on by itself. Advance it by hand."
- unknown code: code with underscores as spaces.
### Stepper (`support.ts:runnerSteps`, :134)
- Step labels "Start the circuit" / "On station" / "Reading time" / "Consultation". Sublabels: "Opens the room for everybody" | "Running" | "Ended"; "After the circuit starts" | `{person} · station {i} of {n}` | `{n} of {m} stations sat` | "Between stations" | "Waiting for the next station"; "Once somebody is on station" | "The candidate is reading the brief" | "Done for this station" | "Not running"; "After reading time" | "Patient is live · {station}" | "Waiting for the patient to join" | "Finished".
### Clock block (:147-158)
- Big ExamClock labelled by phase; caption "Server clock" (:156).
### Supervisor controls (`SupervisorControls.tsx`)
- Ended circuit: "This circuit has ended." + (sign_off_results) " Its stations can still be marked and its record read." (:69-70); no buttons.
- Failure Alert (danger) text from the failed action + "Dismiss" (:87).
- Not started: "Start circuit" (:102).
- Started: "Next station" (:113), "Pause" / "Resume" (:129), "Extend the clock" (:138), "Reset the clock" (:147), "Resend the patient" (:156), "End circuit" (:166, danger). All disabled while busy or reconnecting.
- Checkbox (started only): "Moves to the next station automatically when time is up. When off, the circuit waits for you before each new station." (:185).
### Override dialogs (`OverrideDialog.tsx`; requests at SupervisorControls.tsx:200-259, TurnStrip.tsx:167-185)
Common: buttons "Cancel" and the commit label, busy label "Working…" (:88); field "Reason (kept with the record)" max 500, placeholder "The fire alarm went off" (:110-118), optional; error Alert shows the last failure.
| Title | Lead | Commit |
|---|---|---|
| "Pause the circuit" | "The clock stops for everybody. The patient stays in the room." | "Pause" |
| "Resume the circuit" | "The clock starts again from where it stopped." | "Resume" |
| "Extend the clock" | "Adds time to the phase that is running now, for this station only." + field "Seconds to add" (1-3600, default 60) | "Add the time" |
| "Reset the clock" | "Restarts the phase that is running now from its full duration." | "Reset it" |
| "Resend the patient" | "Dispatches a new patient to the station that is running. The consultation starts over for this candidate." | "Resend" |
| "End the circuit" (danger) | "Stations nobody has sat are recorded as skipped. This cannot be undone." | "End the circuit" |
| `Jump to {person}` | `The circuit moves to {station}. Stations passed over are recorded as skipped.` | "Jump to it" |
| `Redo {station}` | `{person} sits this station again with a new patient. The first attempt stays on the record.` | "Redo it" |
### Turn strip (training only; `TurnStrip.tsx`)
- Heading "Stations on this circuit" (:54); hint when live "Tap a name to jump the circuit to that station" (:58).
- Chip per slot: numbered, person label (name, email, else "Candidate"), station title (else "Station"); chip button title "Jump the circuit to this station" (:133); "Patient is live" (:152); link-button "Redo this station" on completed slots (:160).
### Station progress (`StationProgressList.tsx`; heading "Station progress", CircuitRunner:174)
- Columns "Candidate", "Station", "Phase", "Left", (sr-only) "Marking" (:43-47). Row: initials, person, "With the patient" when agent live (:110); `{n} · {station}`; progress Badge: "Not started" / "Reading" / "In consultation" / "Completed" / "Skipped" (`support.ts:PROGRESS_LABEL`); extra Badge "Marked" when reviewed; live countdown; action ButtonLink "Mark" or "Review" (when has_review) to `/slots/{id}/review[?attempt=]`, shown once markable (:136).
- Empty: EmptyState "No stations on this circuit yet." (:35).
### Station content (`SupervisorReadingBrief.tsx`, active station only)
- Heading `Station content` or `Station content: {title}` (:57); sections collapsible (staff sections from marking/content slice); fallback sub-headings "Reading brief", "Full content" (:103, :113); "No content available for this station." (:121).
### The room (`ObserverPanel.tsx`)
- Title "The room"; status "Listening" / "Not connected" (:44-46); buttons "Stop listening" (:52) / "Listen in" (:64, disabled with title "The circuit is not running" when not live).
- Idle text "You can hear the consultation without being heard in it. Nothing you do here reaches the candidate or the patient." (:97). Failure Alert = error message. ExamClock repeated.
- Occupants list (exam, subscribe-only): "The patient" with "In the room" / "Not in the room yet"; "The candidate" with "Not in the room yet" / "In the room"; "Speaking" (:118-163).
- Training (can_publish): `ObserverVideoGrid`: icon buttons "Mute microphone"/"Unmute microphone", "Turn camera off"/"Turn camera on" (:47,66); warning "Could not access your {camera|microphone}. Check browser permissions and try again." (:36); tiles labelled "The patient" / "You" / name or "The candidate"; "Audio only" / "No camera" (:112).
### Mark a finished station (`LiveMarkingSidebar.tsx`)
- Fold section title "Mark a finished station" (:37); tablist aria-label "Finished stations" (:38); one tab per finished station (title) with Badge "Unmarked" when not reviewed (:59); body = embedded `SlotReview` (marking-owner screen, out of scope).
### Circuit feedback (`CircuitFeedbackCard.tsx`, hidden if no slots)
- Panel title "Share this circuit's feedback"; description "Shares one summary of all the marking on this circuit. Candidates see it as their feedback. If you edit it and share again, the new version replaces the old one." (:98-99). LITERAL "Candidates".
- `Marked on {m} of {n} station(s)` (:103); sr-only label "Notes on the circuit as a whole"; textarea placeholder "Anything to say about the circuit as a whole (optional)" (:114).
- Published: Alert success `Published {date}. Publishing again replaces it.` (:120); else "Not published yet." (:124). If none marked: "You can share feedback once at least one station has been marked." (:129).
- Button "Publish circuit feedback" / "Publish again" (:141), disabled if busy, offline or none marked.
- Loading/error: AsyncBoundary defaults.
### What was changed by hand (`InterventionsLog.tsx`)
- Collapsible heading "What was changed by hand" with "Show" / "Hide" (:44-45).
- Entries: action labels "Advanced to the next station", "Paused", "Resumed", "Clock extended", "Clock reset", "Patient resent", "Station redone", "Jumped to a station", "Auto-advance changed" (:11-19), reason or "No reason was given." (:81), timestamp.
- States: spinner; error Alert "That record could not be read. {message}" (:69); empty "Nobody has stepped in on this circuit." (:69).
### Add somebody to this circuit dialog (`AddTraineesDialog.tsx`, training only)
- Title "Add somebody to this circuit"; lead "They are given a station at the end of the circuit, in the room that is already open." (:119-120). Buttons "Cancel", commit "Add them" / `Add {n} people`, busy "Adding…"; disabled when none picked.
- Roster checkbox list: name (or email), email; not-signed-in rows disabled with "{email} · Not yet joined: they can be added once they have signed in." (`latecomers.ts:4`).
- Empty "Everybody on your roster is already on this circuit." (:~155).
- After picking: select "Station" with default option "The station this circuit is running" and the circuit's stations (`{title} · v{n}`, else "Untitled station"); hint 1 person "They take their turn after everyone already on the circuit." / many "Everyone you add takes the station chosen here, after everyone else on the circuit. To spread them across different stations, rebuild the circuit." (:~203).
- Refusals: trainee_already_on_circuit "Already on this circuit, so nothing was added. {msg}"; station_not_on_circuit "That station is not on this circuit. Pick one from the list, or leave it to the station being run. {msg}"; not_permitted_in_mode "An examination cannot take a late arrival: it is one candidate through every station."; else `assessErrorMessage`.
### States
- Loading: AsyncBoundary spinner; error "That did not load"/"Try again". Stream drop: header badge "Reconnecting" and controls disabled (no text banner).
### Toasts
- None.


## Dashboard / Overview (`/dashboard`)
Files `domains/assess/dashboard/OrgDashboard.tsx`, `LiveNow.tsx`, `SupervisorCircuits.tsx`, `support.ts`. Route screen `AssessDashboard` (`surfaces/assess/screens.tsx:66`): without `run_circuits` it renders `TraineeHome` (trainee portal, out of this part). With it: one screen; halves are gated inside: `can(manage_team)` shows the At a glance tiles (OrgDashboard:44,97), `can(run_circuits)` shows Running now and Assigned to you (:95,103), `can(schedule_sittings)` + `ready_to_run` shows the header commit (support.ts:77).
### Header
- Eyebrow = organisation name (:79); title = `greetingFor(name, now)` (`trainee/support`).
- Commit button `w.scheduleSitting` = "Schedule a sitting" / "Schedule an assessment" (hire), with plus icon -> `/sittings/new` (:83-86). Shown only when `homeCommits` = "header".
### Getting started card (`Setup`, :148-170; hidden when nothing left to do)
- Heading "Getting started" (:158). StepGuide steps clickable (navigate to the step path); line = next step sentence; one ButtonLink = next action label; variant commit when `homeCommits` = "card" else secondary (:165). All LITERAL (not `w.*`).
- Steps (`support.ts:37-44`: label / todo note / line / action / path); done note "Done":
  - "Marking scheme" / "Publish one" / "Start with a marking scheme: what candidates are marked against." / "Write a marking scheme" / `/authoring/rubrics`
  - "Exam" / "Publish one" / "Next, an exam: adopt one the platform publishes, or write your own on the marking scheme." / "Adopt or write an exam" / `/programmes`
  - "Programme" / "Add one" / "Every sitting belongs to a programme, which offers an exam." / "Add a programme" / `/programmes`
  - "Station template" / "Publish one" / "Next, a station template: the shape your stations take." / "Make a template" / `/authoring/station-templates`
  - "Stations" / "None to run" / "Your own cases count, and so does the platform library for an exam you offer." / "Add stations" / `/authoring/stations`
  - "Team" / "Invite a supervisor" / "Somebody besides you has to be able to supervise a circuit." / "Invite your team" / `/team`
  - "Trainees" / "None added" / "Add the people who will sit your examinations and training sessions." / "Add trainees" / `/trainees`
  - "First sitting" / "Not scheduled" / "Everything is in place. Schedule the first sitting." / "Schedule a sitting" / `/sittings/new`
### Running now hero (`LiveNow.tsx`, `run_circuits` only; renders nothing when nothing is running)
- Eyebrow "Running now" (:40); title `{sitting} · {circuit}` (:41); candidates line (see label rules below).
- Buttons "Open console" -> `/circuits/{id}` (:45); "All {n} running" -> `/live` when more than one (:49).
- Badge "Needs a look" (danger) when alerts or recording missing (:58), else status badge (`circuitStatus`: "Paused" / "Between stations" / "Reading time" / "Consultation" / "Running", `support.ts:88-92`); ExamClock with seconds left.
- Error (stream, nothing to show): Alert "The live view is unavailable: {message}" (:34).
### At a glance (`Counts`, `manage_team` only, :173-192)
- StatGrid label "At a glance"; tiles (each a link): `w.Trainees` ("Trainees" / "Candidates") -> `/trainees`; "Staff" -> `/team`; "Your stations" -> `/authoring`; `w.Sittings` ("Sittings" / "Assessments") -> `/sittings`.
### Assigned to you (`SupervisorCircuits.tsx`, `run_circuits` only)
- Section eyebrow "Assigned to you" (:90). Rows link to `/circuits/{id}`: title `{sitting} · {circuit}`; meta `{mode} · {n} station(s)` + ` · {scheduled}`; Badge "In progress" / "Ready to run" (:79); in-progress first. Ended circuits are filtered out.
- Empty (only when the person is not an admin, `sayWhenEmpty`): row "Nothing is assigned to you right now." / "A circuit appears here when an administrator names you its supervisor." (:48-49); link row "Your last ended circuit" with `{sitting} · {circuit}` (:55-56).
- Loading Spinner; error Alert = error message.
### Recent sittings (:105-135)
- Section eyebrow `Recent {w.sittings}` ("Recent sittings" / "Recent assessments"); link `All {w.sittings}` -> `/sittings` (:109).
- Rows -> `/sittings/{id}`: name, meta `{date} · {mode}` or mode, Badge `humanise(status)`.
- Empty row "Nothing scheduled yet." (:114).
### States
- Loading/error: AsyncBoundary defaults (Section 0). No toasts, no dialogs.

## Live board / Now running (`/live`)
File `domains/assess/dashboard/LiveBoard.tsx`. Route screen `AssessLiveBoard` (`surfaces/assess/screens.tsx:97`); no client gate (api gates); the SSE stream (`useEventStream`) only opens with `run_circuits`.
### Header
- Title "Now running" (:62); subtitle "Every circuit that is live in your organisation." (:63); Badge "Live" / "Reconnecting" (:67), `run_circuits` only.
- Stream error Alert "The live view is unavailable: {message}" (:74).
### Running (AsyncBoundary on initial read)
- Empty: EmptyState "Nothing is running." / "Circuits appear here the moment a supervisor starts one." (:83-84).
- Warning Alert (when `worker_running` is false): "The background worker is not running. This screen still moves due circuits on, but marking and clearing patients from rooms wait until it is back. Tell your platform admin." (:92-94).
- Hero: eyebrow "Live"; title `{n} circuit running` / `{n} circuits running` (:99); body = first sitting name; button `Open {circuit name}` -> `/circuits/{id}` (:106).
- Section "Running" (:112); per-row link to console: title circuit name; meta `{sitting} · {mode} · {station} · {candidates} · {supervisor|"no supervisor named"}` + ` · room open`; station text `Station {i} of {n} · {title}` or `Between stations · {m} of {n} sat` (:240-243); candidates text "Nobody on this circuit" / names joined with " and " / `{a}, {b} and {n} more` (support.ts:130-133); supervisor fallback "Supervisor".
- Row trailing: stage strip (md+, aria-label "Stage"): "Reading", "Consultation", "Between" (:209-211); status Badge (`circuitStatus`); ExamClock.
- Per-circuit notices: danger Alert `{circuit}: a consultation is running but is not being recorded. Open the circuit and send the patient in again.` (:285); warning Alerts `{circuit}: {alertCopy(code)}` (same four alert sentences as the console).
- Row order: alerts (+2), recording missing (+2), paused (+1), then soonest to run out (`boardOrder`).
### Earlier (:141-203)
- Section aria-label "Earlier"; group eyebrow `Earlier · {Today|Yesterday|weekday, day month}` (support.ts:160-163).
- Rows (link to console when circuit still exists): title circuit name; meta `{sitting} · {mode} · {n} candidate(s) · {done} of {total} stations` + ` · ended early`; trailing `{start}–{end}` or `ended {end}` (en-GB hh:mm).
- Empty: "Nothing has finished yet." / "Circuits appear here when they end." (:152).
- Button "Show earlier" / "Loading…" (:200); Alert `Could not load more: {message}` (:190).
### Toasts and dialogs
- None.

Screens: 8, controls: ~169

<!-- parts/2-results-trainee.md -->
# Part 2: results, review, trainee, settings, reporting (baseline inventory)

Paths are under `/Users/yahayakenny/Documents/Projects/osceguide/web/src/`. Read-only inventory; strings quoted from code.

Conventions
- Word map (`domains/assess/vocabulary.ts:18-44`, hook `useAssessWords.ts:5`; hire when `surface === "hire"`):
  sitting/sittings/Sitting/Sittings = institution `sitting`/`sittings`/`Sitting`/`Sittings`, hire `assessment`/`assessments`/`Assessment`/`Assessments`;
  trainee/trainees/Trainee/Trainees = `trainee`/`trainees`/`Trainee`/`Trainees`, hire `candidate`/`candidates`/`Candidate`/`Candidates`;
  People = `People` / `Candidates`; scheduleSitting = `Schedule a sitting` / `Schedule an assessment`; addPeople = `Add people` / `Add candidates`.
- Shared foundation defaults (not repeated per screen): `AsyncBoundary` (`foundation/ui/AsyncBoundary.tsx`) loading = centred large spinner (:59), error = Alert title "That did not load" + message (fallback "Something went wrong.") + button "Try again" (:68-71). `ConfirmModal` default cancel "Cancel", busy label "Working…" (`foundation/ui/ConfirmModal.tsx:48-49,129`). Modal (`foundation/ui/Modal.tsx`) has a close-circle icon button unless hidden.
- Routing: every route file renders `<Screen name=... slug=...>` (`app/app/[workspace]/screen.tsx`); an arm whose manifest does not own the name 404s. Hire has `screensFrom: "assess"` (`surfaces/hire/surface.ts:39`) so it renders the identical components. Screen map: `surfaces/assess/screens.tsx:241-259`.
- Nav gating (`surfaces/assess/surface.ts:35-82`): staff menu (needs `run_circuits`) = Overview, Sittings, Results, Now running, People, Reporting, Team (`manage_team`), Build, Stations/Programmes (`author_content`). Everyone else (no `run_circuits`) = "My training", "Practice sessions", "Self practice". Hire (`surfaces/hire/surface.ts:14-31`): candidate sees only "My assessments"; staff = Overview, Assessments, Results, Now running, Candidates, Team (`manage_team`), Build. **Hire nav has no Reporting item and no Self practice item, but the `reporting`/`myPractice` screens are in the shared screen list.**
- Permissions (`foundation/session/permissions.ts:10-19`): `read_org`, `manage_team`, `run_circuits`, `schedule_sittings`, `sign_off_results`, `export_results`, `author_content`, `administer_platform`. Pages are not individually permission-gated in the browser except where noted; the API refuses staff reads to trainees.

---

## Results index
- Route: `/app/[workspace]/results` (`app/app/[workspace]/results/page.tsx:12`, screen `resultsIndex`, metadata title "Results"). Seen by staff (nav needs `run_circuits`); both institution and hire. Component `domains/assess/results/ResultsIndex.tsx`.
- Heading: `title="Results"` (:93), subtitle `Each ${w.sitting} with how far its decisions have got.` (:94) -> institution "Each sitting with how far its decisions have got." / hire "Each assessment with how far its decisions have got."
- Tabs and filters (`B2CSegmentedTabs`, aria-label "Filter results", :97): "Needs a decision" (id needs_decision, default; rows with not_decided>0 or draft>0, `support.ts:332`), "Ready to release" (rows with signed_off>0, :333), "All" (:102-104).
- Table columns (:35-75): `${w.Sitting}` (link to `/sittings/{id}/results`, :45) = "Sitting"/"Assessment"; "Date" (value `toLocaleDateString()` or "Not scheduled", :59); "Mode" (capitalised row.mode); "Candidates"; "Not decided"; "Draft"; "Signed off"; "Released" (:70-74; column headers are literal "Candidates" in both labels).
- Row actions: row name link to the sittings results screen (:44-50).
- States:
  - loading: AsyncBoundary default spinner; error: AsyncBoundary default ("That did not load", "Try again").
  - empty (no rows): title "No results yet", description `Results appear here once ${w.sitting === "sitting" ? "a sitting" : "an assessment"} has ${w.trainees}.` -> "Results appear here once a sitting has trainees." / "...an assessment has candidates." (:111-112)
  - filtered empty table: "Nothing here." (:128)
  - truncated notice (role=status): `Showing the {n} most recent {w.sittings}. Older ones are not listed here.` (:118-121)
- Toasts: none.

## Sitting results (cohort report)
- Route: `/app/[workspace]/sittings/[sittingId]/results` (`.../sittings/[sittingId]/results/page.tsx:12`, screen `sittingResults`, title "Results"). Staff; both arms. Component `results/Results.tsx` (renders CandidateCard, ReleaseAll, CohortRanking, StepGuide).
- Heading: back link label "Sitting" to `/sittings/{id}` (:89, **literal "Sitting" in hire too**); eyebrow = sitting name (:90); title "Results" (:91); subtitle `${stations_marked} of ${stations} stations marked · ${decisions_released} of ${candidates} released` (:92).
- Buttons: "Download CSV" (secondary, only with `can(export_results)`, :95-103).
- Stat tiles (StatGrid label "Outcomes", :170-182): "Passed", "Failed", "Inconclusive", "Withheld", "Undecided", "Awaiting marking".
- Step guide (shown when nothing to release; also inside ReleaseAll): step rail from `sittingSteps` (`domains/assess/sittingSteps.ts`): steps "Schedule", "Circuits", "Run", "Mark" plus "Decide", "Release" (exam mode only; training stops at Mark, :127). Notes: "Date set"/"No date" (:116); "None yet"/`N circuit(s)`/`N candidate(s) assigned`/"Candidates sat" (:122); Run notes "Circuit ended, nobody sat", "All finished", `N of M stations sat`, "Nobody has sat yet", `N of M finished`, "Not started" (:63-81); Mark/Decide/Release notes via `countNote` = `N of M marked|decided|released` or "Not started" (`results/support.ts:320-322`).
  Next-step lines (`sittingNext`, :135-189): "N result(s) signed off and not yet released." / "N result(s) signed off, waiting for an administrator to release them."; "Set a date for this sitting."; "Add a circuit so candidates can take this sitting."; "The circuit ended and nobody sat. Open it to see what happened, or add another circuit."; "A circuit is running. Follow it from its console."; "Start the circuit from its console when everyone is ready."; "Marking is not finished. Review each station on the results page."; "Record and sign off each candidate's outcome."; "Waiting for an administrator to record and sign off each outcome."; "Sign off the remaining outcomes, then release them."; "Waiting for an administrator to sign off and release the results."; "Every station has been marked." (training) / "Every result has been released." (**literal "sitting" in the schedule line even in hire**).
- Candidates table (`section aria-label="Candidates"`, :128-153): column headers "Candidate", "Score", "Outcome", "Status", sr-only "Actions".
- Row actions: see Candidate row.
- States: loading/error AsyncBoundary default; empty (no candidates) `EmptyState title="Nobody has sat this yet."` (:111). Download error: Alert danger with the error message (:107).
- Toasts: none (inline Alerts).
- Gating: `releasable` list and ReleaseAll only if `can(sign_off_results)` and not training (:69); download only `can(export_results)`.

## Cohort ranking ("Review order", exam sittings only)
- Mounted by Results when `sitting.mode === "exam"` (Results.tsx:126). `results/CohortRanking.tsx`.
- Section eyebrow "Review order" (:42); intro `${cohort_size} candidate(s), with unfinished reviews first, then the weakest results.` (:44); row title `${rank}. ${name}`, meta `${cohortSubtitle} · ${completion}% complete` (:49-50, `formatCompletion` returns "-" when unknown); priority badges from PRIORITY_LABEL: "Urgent review", "High priority", "Standard", "Low priority" (`support.ts:98-101`).
- Buttons: "Export readout" (ghost; busy label "Exporting…"; only with `can(export_results)`; `ReadoutExport.tsx:66`). Note: "This sitting has no read-out to export." (warning, :44); failure Alert shows error message. Downloads `{sitting_id}-exam-readout.md` (`support.ts:209`) with sections "# {name}: examination read-out", "## Cohort", "### Review priorities", "## Candidates" ("Nobody was rostered onto this examination."), "## Recommendations", "## Methodology" (`support.ts:228-284`).
- States: loading Spinner (:32); error Alert danger message (:33); empty -> renders nothing (:39).

## Candidate row (CandidateCard)
- `results/CandidateCard.tsx`; table row in Results; all staff see it, decision part gated on `can(sign_off_results)` (:51).
- Cells: initials avatar; name (`candidateName`: name, else email, else "Candidate", `support.ts:115`); subtitle `${stations_marked} of ${owed} stations marked` + ` · overall ${ratingLabel}` (:89-90); score `formatScore` = `NN/100`, missing = "No automatic score" when stations marked, else "Not assessed" (:96, `support.ts:119-121`); outcome Badge (outcomeLabel "Pass"/"Fail"/"Inconclusive"/"Withheld") or "Not decided" (:104); status Badge = furthest reached step: "Marked"/"Reviewed"/"Decided"/"Signed off"/"Released", default "Not marked" (`candidateProgress.ts:70-73`).
- Row actions: "Result PDF" (ghost sm; only when released and `can(sign_off_results)`, :123); "Open" / "Close" toggle (aria-label `Open {name}` / `Close {name}`, :131-134).
- Expanded panel: section "Stations" (B2CGroupedSection eyebrow, :149); empty "They have not sat anything yet." (:151); each station row is a link to `/slots/{slotId}/review?attempt=..&sitting=..` (:205) with title = station title or "Station", meta `${circuit_name} · ${slot_status with _ -> space}`, trailing rating Badge (`ratingLabel`) else "Awaiting review" / "Absent" / "Not marked" (:216). Fold section "The decision" (:162): for non-sign-off roles the text "An institution administrator records, signs off and releases the decision. Its stage is shown in the row above." (:173-174, **literal "institution" in hire**).
- Errors: Alert danger with PDF download error (:142).

## Candidate decision form
- `results/CandidateDecision.tsx` + `DecisionParts.tsx`; inside the "The decision" fold, for `can(sign_off_results)` only.
- States: no linked account: Alert warning "This candidate took the exam but is not on your trainee list. Add them to the list, then record the decision." (:59, **literal "exam"/"trainee"**); loading Spinner; error Alert with `assessErrorMessage`.
- Step rail (aria-label "Steps"): "Marked", "Reviewed", "Decided", "Signed off", "Released"; notes `N of M marked|reviewed`/"Not started"; "Reviews not complete"; outcome label or "Not decided"; "Signed off"/"Not signed off"; "With the candidate"/"Not released" (`candidateProgress.ts:29-66`).
- Header: Badge workflow label ("Draft", "Signed off", "Released"; `support.ts:79-81`), "Revision {n}" (:170).
- Fields: fieldset legend "Outcome" with toggle buttons (aria-pressed) "Pass" / "Fail" / "Inconclusive" / "Withheld", each with hint "Met the standard." / "Did not meet the standard." / "Not enough was assessed to decide." / "Decided, but held back, for example during an investigation or an appeal." (`DecisionParts.tsx:166-188`, `support.ts:32-42`); suggestion line `Suggested from the marks: N of M stations passed. You decide.` (`support.ts:178`); hire-only Select "Recruitment outcome" (`DecisionParts.tsx:33`) hint "Whether you are taking this candidate on. The candidate does not see it." options "Not recorded", "Pending", "Hired", "Reserve list", "Not hired", "Withdrawn" (`support.ts:50-54`); textarea label "Rationale" (max 4000, rows 4), placeholder "Why this outcome, in the words you would use to a candidate or an appeal panel." (:192-199).
- Buttons: "Save draft" (secondary); "Sign off" (commit, check icon; disabled while blockers); signed off: "Back to draft" (ReopenButton); "Preview what they'll see" (secondary, whenever a decision exists, `DecisionParts.tsx:74`).
- Blockers Alert (warning, title "Before this can be signed off"): "An outcome has to be chosen." ; "Write down the reason, so anyone can see why this was decided later." (`support.ts:150-152`).
- Dialogs: ReopenButton ConfirmModal title "Back to draft?", body "The sign-off is withdrawn and the decision becomes a draft you can change. It has to be signed off again before it can be released.", confirm "Back to draft", cancel "Cancel" (`DecisionParts.tsx:115-117`). Result preview Modal title "Result preview" (:77), Alert info "Preview of the released result, as the candidate sees it." or "Preview of the last saved version. The candidate cannot see this until it is released." (:94-95); body is `ResultView` (see trainee).
- Released view (`ReleasedDecision`): Badge "Released"; `Released {datetime}.` or "Released."; "Once released, a decision cannot be edited. Any correction is saved as a new version."; `Recruitment outcome: {label}`; rationale text.
- Stale notice (`StaleNotice`): Alert warning title "This decision has changed since you loaded it", body "Someone else saved a change while you had this open, so yours was not saved. Nothing is lost. Load the latest version and make your change again.", button "Load the latest version" (:195-201).
- Toasts (inline success Alerts): "Draft saved." (:223); "Signed off. It is not with the candidate until it is released." (:242); "Back to draft. Change what you need, then sign off again." (:260). Failure Alert danger via `assessErrorMessage`.
- Footer notes: signed off and not releasable: "Cannot be released: a withheld or inconclusive outcome is not sent to the candidate." (:271, `support.ts:309-310`); signed off and releasable: "Signed off. Release it from the button at the top of the results, together with any other signed-off results." (:275); "Sign-off covers the marks as they were at the time. If a station is re-marked afterwards, the result must be reviewed and signed off again before it can be released." (:280).

## Release all (ReleaseAll)
- `results/ReleaseAll.tsx`; shown in Results when signed-off, unreleased candidates exist and `can(sign_off_results)` and exam mode.
- StepGuide (see sitting results) with button `ReleaseButton` (commit, send icon) labelled `Release ${n} signed-off result(s)` ("Release 1 signed-off result", "Release 3 signed-off results"; :90), disabled when none chosen.
- Dialog (ReleaseButton, `DecisionParts.tsx:150-155`): title `Email 1 candidate their result?` / `Email N candidates their result?`; body "Each can read their outcome as soon as it is released, and a released result is final."; confirm "Release"; cancel "Cancel".
- Panel title "Candidates to release", description "Untick anyone to hold their result back." (:96); fieldset legend (sr-only) "Candidates to release"; checkboxes: "All {n}" (when >1) and one per candidate (name, email, or "Candidate").
- Result Alerts: `{n} released` + `, {k} refused.` or "." (success/warning, :132); danger Alert title "Not released" listing lines `{name}: {reason}`; reasons: "has no linked account, so the result cannot be released" (`support.ts:182`), "the marking changed after sign-off, so sign it off again", "not signed off, or already released", "a withheld or inconclusive outcome is not sent to the candidate", "the decision was changed by somebody else; reload and check it", "no decision recorded", `refused ({code})` (`support.ts:305-316`).

---

## Slot review ("Mark this station")
- Route: `/app/[workspace]/slots/[slotId]/review?attempt=<id>&sitting=<id>` (`app/app/[workspace]/slots/[slotId]/review/page.tsx:19`, screen `slotReview`, title "Review"). Staff (reached from candidate rows; every staff role may review, per `sittingSteps.ts:176`). `domains/assess/SlotReview.tsx`. `attempt` and `sitting` default to "" (no attempt = "Nobody has taken this station").
- Heading: title "Mark this station" (:75), subtitle "The automatic marking, your marks and the admin's review." (:76). Header action: CandidateStepper when `sitting` query present.
- Permission fork (`SlotReview.tsx:119-120`): `can(sign_off_results)` -> "admin" form (Admin's review) else "mine" form (Your marks). One form per person.
- Banner: Alert warning "You are not named on this station's circuit, so its automatic marking is not shown to you." (:81; when marking read returned 403).
- Step guide (`slotReviewSteps.ts`): steps "Automatic marking" (notes "Not taken", "Not ready yet", "Marking failed", "Could not be marked", "Not available", "Ready") then "Admin's review" (admin) or "Your marks" (others) (notes "Not started", "Draft", "Submitted"). Next line: "Your marks are submitted." / "Rate each area, then submit your marks." / "The admin's review is complete." / "Write the admin's review, then complete it."
- Layout panels: FoldSection "Your marks" (meta Badge "Submitted"/"Draft", :210-215) OR FoldSection "Admin's review" (description "One overall mark for the station. This is the mark that counts.", :261-263); Panel "What the reviewers agreed" (:269); right column MarkingPanel + AttemptTranscript.
- Fields (Your marks): per-domain rating inputs (ReviewFields, see below); textarea "Notes" placeholder "What you saw, in the words you would say to them." (:231,238); read-only once submitted.
- Buttons (Your marks, hidden once submitted, :242-256): "Withdraw draft" (ghost; only when a draft exists), "Save draft" (secondary), "Submit review" (commit); each shows a spinner while busy.
- Toasts (inline Alert success, :176): "Draft saved" / "Review submitted". Error Alert danger via `assessErrorMessage`.
- States: loading/error AsyncBoundary default; retry-marking error shown in MarkingPanel; no empty state of its own.
- `assessErrorMessage` copy relevant here (`errorCopy.ts:20-27`): review_conflict "Someone else changed this review while you had it open. Reload the page and make your changes again, so theirs are not lost."; review_incomplete "Rate every required area before completing the review."; nothing_to_review "Nobody took this station, so there is nothing to review."; invalid_review_status "A review can only be saved as a draft or completed."; reviews_pending "A review of this candidate's stations is still a draft. Complete it, or ask its author to withdraw it, then sign off."; review_not_draft "Only a draft review can be withdrawn. A completed review is edited instead."; review_not_found "That review no longer exists. Reload the page."; invalid_rating "One of the ratings is not one this station accepts. Pick again from the list."; rubric_not_found "This station has no marking scheme, so it cannot be marked."; rubric_version_not_found "The marking scheme for this station is missing a version. Ask the station's owner to republish it." Full decision/circuit/roster copy in `errorCopy.ts:10-53`.

### Candidate stepper (header of slot review)
- `domains/assess/CandidateStepper.tsx`. Shows nothing while loading or with <2 candidates. Text `Candidate {position} of {total}` (:27); buttons (links, secondary sm) "Previous", "Next candidate" (:36,46) to the neighbouring candidate's review of the same station. Error text: "Could not load the other candidates." (:20).

### Marking panel (automatic marking)
- `results/MarkingPanel.tsx`. With a result and rubric: `RubricFeedback` heading "Automatic marking", narrow (:30; internal strings in `capabilities/feedback/RubricFeedback.tsx`, e.g. empty "No feedback recorded" at :69).
- Else a Panel with `markingNotice` (`slotReviewSteps.ts:39-56`): "Nobody has taken this station, so there is no automatic marking."; "Automatic marking is not ready yet. It appears here when it finishes."; "Automatic marking failed. Retry it, or mark this station without it."; "This station was taken, but it could not be marked because its exam had no marking scheme. It needs to be sat again; you can still record your own marks."; `This station was taken, but it could not be marked ({reason}). You can still record your own marks.`; "This station was taken before the exam had a marking scheme, so there are no automatic marks and there will not be." (**literal "exam"**).
- Button (only when failed): "Retry marking" (busy label "Retrying..."); error Alert danger with message.

### Review fields (shared by examiner and lead forms)
- `results/ReviewFields.tsx`, `RatingInput.tsx`. Empty form: "This station's marking scheme has nothing to rate, so there is nothing to agree or disagree with. Your notes are still saved." (:39).
- Per domain: FoldSection titled with the domain label, Badge "Required" (xs) when required; per field "Machine: {rating label}" (:66); competency rows show field label; lead form adds per-domain textarea (sr-only label `Note on {domain.label}`, placeholder `Why this rating for {domain.label}`, :93,99).
- RatingInput kinds (`RatingInput.tsx`): enumerated scale / boolean = segmented buttons labelled by `ratingLabel`; short integer range (<= 11 values, highest first) = numeric buttons; otherwise number input (aria-label = field label, placeholder `out of {max}`). Group aria-label = field label.
- Footer: "Still to rate before completing: {a, b}." (:112).

### Admin's review (GpLeadReview, `can(sign_off_results)` only)
- `results/GpLeadReview.tsx`. Loading Spinner; error Alert danger with message (:70-71).
- Header: Badge "Completed"/"Draft"; "Revision {n}" (:149-152).
- Fields: ReviewFields with per-domain notes; "Overall" segmented group (aria-label "Overall") buttons "Green" / "Amber" / "Red" (:25-27); textarea "Notes" placeholder "What you saw, in the words you would say to them." (:177,182).
- Buttons: "Save draft" (secondary); "Complete review" (commit), relabelled "Save changes" once completed (:204).
- Toasts: "Review completed." / "Draft saved." (`reviewForm.ts:192`); failure Alert (warning when `review_conflict`, else danger).
- Footer note: "Rate every required area before completing the review, so candidates never see a half-finished one." (:209).

### Reviewers summary ("What the reviewers agreed")
- `results/SlotReviewers.tsx`. Empty: EmptyState "Nobody has finished a review of this station." with description `{n} in progress.` when drafts exist (:39-40). Otherwise: `{n} completed review(s)` + ` · {d} still in progress`; Badge `Agreed: {rating}`; pass/fail badge from `passWord`; per-domain rows (label + rating Badge); note "Where reviewers disagreed, the lower rating is the one shown." (:74).

### Transcript panel (AttemptTranscript, on slot review)
- `domains/assess/AttemptTranscript.tsx`; renders nothing without an attempt id (:40).
- Card "What was said" description "Everything said in the consultation. The marks are shown separately." with button "Load the transcript" (secondary sm; loaded on click, :59).
- Loading: Spinner label "Loading the transcript" (:68). Loaded: description "The whole consultation, in order." or "The consultation is still going. This is everything said so far."; button "Download" (ghost, disabled if no messages; file `transcript-{attemptId}.txt`, :116,124); scrollable `TranscriptView` (its own empty: "No speech was recorded for this consultation.").
- Error: Alert title "This transcript is not yours to read", body "Only the supervisor named on this circuit can read what was said in it." (warning, for `attempt_not_yours`/`forbidden`) else danger with the error message (:81-85).

## Attempt record ("Your consultation")
- Route: `/app/[workspace]/attempts/[attemptId]` (`app/app/[workspace]/attempts/[attemptId]/page.tsx:12`, screen `attempt`, metadata "Your attempt"). Anyone with an attempt the API lets them open (candidate or the circuit's examiner); both arms. `domains/assess/trainee/StationRecord.tsx`.
- Headings: eyebrow "Station record", h1 "Your consultation" (:26-27), sections "Feedback" (renders capability `AttemptFeedback`) and "Transcript" (`TranscriptView` in AsyncBoundary) (:31,36).
- States: transcript loading/error AsyncBoundary default; empty transcript text in `TranscriptView`. No buttons of its own (capability components own theirs).

---

## My training (trainee home)
- Route: `/app/[workspace]/trainee?slot=<slotId>` (`app/app/[workspace]/trainee/page.tsx:16`, screen `myTraining`, metadata "My training"). Seen by anyone without `run_circuits` (nav item "My training" in institution, "My assessments" in hire, `surface.ts:61` / `hire/surface.ts:18`); not permission-gated in browser. `domains/assess/trainee/TraineeHome.tsx`. Live via SSE `mySittingsStreamPath` with a plain read as first frame.
- Heading: eyebrow = org name else greeting ("Good morning"/"Good afternoon"/"Good evening", `support.ts:260-262`); title `Hello, {first name}.` or "Hello." (:68); header Badge "Live" (connected) / "Updating" (:71).
- Join-link banner when `?slot=` present (:103-116): info `You were sent to {station | "one of your stations"} on {sitting name}.` + link "Open it" + ". The room is open now." or "."; warning "That link is for a station you are no longer booked on. Everything you are booked on is listed below."
- Live turn banner (`LiveTurnBanner.tsx`): section aria-label "Live consultation"/"Live consultations", sr-only h2 "Live now"; hero eyebrow "Today"; title "Your station is open" (exam) with body "Go in and read the brief. The patient joins when the reading time ends." or "Your turn is live" with "Join the room to speak with the patient while your supervisor runs the circuit." (`support.ts:208-217`); text `{sitting} · {circuit}. {body}`; aside Badge "Live"; action = JoinRoom (below).
- Lists: section aria-label `Your ${w.sittings}`; group eyebrow `Your ${w.sittings}` ("Your sittings"/"Your assessments") and `Past ${w.sittings}` ("Past sittings"/"Past assessments").
- Row (link to `/trainee/sittings/{id}`, :152-174): title = sitting name; meta `{summaryLine} · {continueLabel}` + ` · {completed}/{total}`. summaryLine = "Examination" or "Practice circuit" (`modeLabel`) + `{n} of {m} stations completed` (exam) + localised start time (`support.ts:176-185`). continueLabel: "Your station is open", "Paused by your supervisor", "Running now", "Finished: open it for your result and feedback", "Continue", "Not started" (`support.ts:189-196`). Trailing Badges: "Open now" (can_join), "Result released", "Paused".
- "Practise" group (:192-208): row "Self practice" meta "From your organisation" (link `/trainee/practice`); row "Practice history" meta "Past attempts, transcripts and debriefs" (link `/transcripts`, only when the `transcripts` capability is mounted).
- States: loading/error AsyncBoundary default; empty EmptyState title "You are not booked on anything yet", description `When your organisation adds you, your ${w.sittings} appear here, and you are told when one opens.` (:123-124).
- Toasts: none.

## My sitting detail
- Route: `/app/[workspace]/trainee/sittings/[sittingId]` (`.../trainee/sittings/[sittingId]/page.tsx:12`, screen `mySitting`, metadata "Your sitting"). Trainees; both arms. `domains/assess/trainee/MySittingDetail.tsx`. One section per circuit of that sitting.
- Header: eyebrow = weekday/day/month of schedule else mode label ("Examination"/"Practice circuit"); title = sitting name; Badges "Live", "Paused"; button-link "All {w.sittings}" (secondary sm; "All sittings"/"All assessments") to `/trainee` (:116).
- Info Alert (when not joinable, :123-127): exam: title "Before you start", body "Your station opens when your supervisor starts it. Go in straight away: the patient joins when reading time ends, and you need to be in the room by then."; training: title "How a practice circuit works", body "Your supervisor opens the room. Only the person whose turn it is speaks with the patient. Each station's review appears here as soon as your supervisor completes it."
- Hero when `can_join` (:131-141): eyebrow `Station {n} of {total}` (exam) / `Turn {n} of {total}` or "Today"; title "Your station is open" (exam) / "Your turn is live"; body = active station title; action JoinRoom.
- Reading brief (`SlotReadingBrief.tsx`): `StationBrief` sections, else a card heading "Reading brief" with markdown text, else nothing; loading/error AsyncBoundary default.
- Slots group eyebrow "Your stations" (exam) / "Your turns"; empty state EmptyState "Nothing assigned yet", description "When your organisation adds stations for you on this circuit, they appear here." (:148-149).
- Slot row: title `Station {n} · {station title}` / `Turn {n} · ...`; meta "This station could not be marked; your school has been told." (marking failed, **literal "school"**) or "Read this one back below. A finished station cannot be re-entered." (done); Badge "Now" when active else status label: "Completed", "In progress", "Skipped", "Ready", "Not started" (`support.ts:35-46`). Row actions: button-link "Review station" (done) / "Station record" (to `/attempts/{attemptId}`, only with an attempt); "Station feedback" (to `/trainee/reviews/{slotId}`, only when the server says feedback is ready; failure text "Could not check for feedback. Reload to try again.").
- Result link (after circuits): Alert success title "Your result has been released" with link "Read your result" (to `/trainee/results/{sittingId}`); failure Alert warning "Could not check whether your result is released. Reload to try again."
- States: loading/error AsyncBoundary default; not found (EmptyState): title `We could not find that ${w.sitting}` ("sitting"/"assessment"), description "You may have been taken off it, or it belongs to another organisation." (:65-66).

## Join room (JoinRoom, used by trainee home banner and sitting detail)
- `domains/assess/trainee/JoinRoom.tsx`. Auto-joins when `can_join` (the reading phase); manual button otherwise.
- Buttons: "Join" / "Re-join" (commit, door icon, spinner while joining; only when `can_join`, :125); in room: "Leave the room" (danger, :107). Badge "Paused" (:121). Exam clock label from `phaseLabel`: "Reading", "Consultation", "Feedback", "Waiting", "Now" (`support.ts:229-237`). In room tile name "Your patient" (:96).
- Alerts: mic message (danger in room: `{mic.message} The patient cannot hear you until it works.`; warning pre-join: `{mic.message}`); join error Alert danger from `joinFailureCopy` (`support.ts:282-288`): circuit_not_live "This circuit is not open yet. You will be let in when your supervisor starts it."; circuit_not_found "That circuit is not on your list any more. Go back to your sittings."; voice_unavailable "The voice service is not available right now. Wait a minute and try again."; trainee_revoked "Your access to this organisation has been withdrawn. Ask your administrator."; trainee_not_on_roster "You are not on this circuit. Ask your supervisor to add you."; else the server message.

## My result
- Route: `/app/[workspace]/trainee/results/[sittingId]` (`.../trainee/results/[sittingId]/page.tsx:12`, screen `myResult`, metadata "Your result"). Trainee; both arms. `trainee/MyResult.tsx` + `ResultView.tsx`.
- Heading: eyebrow `Released {date}` or "Your result" (:68-72); title "Assessment outcome" (:73).
- Buttons: "Download PDF" (shown once released; busy "Preparing…", :82); "I have read this" (commit; only until acknowledged, one-way, :116); text `You read this on {date}.` once acknowledged (:107).
- Result body (`ResultView.tsx`): hero eyebrow "Outcome", title `{Outcome}, {score} / 100` (score `toFixed(1)`) or `{Outcome}` or "Recorded" when no outcome (:19-20,48); rationale text; section "By station" rows titled station title or "Station" with Badge `{score} / 100` + ` · Pass`/` · Fail`, or "Not scored" (`api.ts:143-146`).
- Closing hero (:121-138): eyebrow "Keep practising", title "Practise on your own", body "Nothing you do here is marked for the record.", button-link "Self practice" (to `/trainee/practice`; **hire has no Self practice nav item but this link still shows**).
- States: Alert info title "Not released yet", body "Your organisation has not released this result. When it is, we email you at the address your organisation holds for you." (null answer or `released_at === null`, :89-91,96-98); download/ack error Alert danger; loading/error AsyncBoundary default.

## My review ("Station feedback")
- Route: `/app/[workspace]/trainee/reviews/[slotId]` (`.../trainee/reviews/[slotId]/page.tsx:11`, screen `myReview`, title "Station feedback"). Trainee; both arms. `trainee/MyReview.tsx`.
- Heading: back button "Back" (router.back, :35), eyebrow "Your review", title "Station feedback".
- Waiting Alert info (server reasons, `api.ts:51-58`): "Not released yet" / "Your result for this sitting has not been released, so the feedback on this station is not shared yet." (**literal "sitting"**); "Not marked yet" / "Your result is out, but the review of this station is not finished yet. It appears here when it is." (`api.ts:57-60`).
- Review body: hero eyebrow "Overall", title = rating label, aside Badge pass/fail word, notes text; section "By domain" rows (domain label + rating Badge); footer `Completed {datetime}`.
- States: loading/error AsyncBoundary default; no buttons beyond Back.

## My practice (Self practice list)
- Route: `/app/[workspace]/trainee/practice` (`.../trainee/practice/page.tsx:12`, screen `myPractice`, metadata "Self practice"). Trainee nav item "Self practice" (institution only, section "practice"); both arms render it. `trainee/SelfPractice.tsx`.
- Heading: title "Self practice", subtitle "Your organisation's stations. Nothing here is marked for the record." (:31-32).
- Fields: `SectionSearchField` placeholder "Search stations" (:61).
- Group eyebrow `{n} station(s) you can sit` (:63); row = station title, meta `{EXAM} · version {n}`, click starts an attempt (`stationAttemptPath`); row action button-link "Past feedback" (ghost sm, `stationFeedbackPath`, :84).
- Footer: `{n} more is a draft and cannot be sat until published.` / `{n} more are drafts and cannot be sat until published.` (:91-92).
- States: loading/error AsyncBoundary default; empty title "No published stations yet", description "Your organisation has not added any stations yet. Ask your administrator when they will be ready." (:39-41).

## Practice station (self practice runner; route outside the assigned list)
- Screen `practiceStation` (`SelfPracticeStation.tsx`); the route file is not in my assigned set. Header (attempt action, no attempt): h1 = station title, "Nothing here is marked for the record." (:71-75); body is capability `StationScreen` (four-step runner, owned elsewhere). Not-available state: Alert warning title "This station is not available", body "It may have been withdrawn, is not published yet, or belongs to another organisation.", link "Back to practice" (:99-108). Create error: "That station is no longer available." (:55).

## Settings (WorkspaceSettings)
- Route: `/app/[workspace]/settings` (`app/app/[workspace]/settings/page.tsx`, capability page, metadata "Settings"; sub-route `settings/referrals/[referralId]` outside this inventory). Every signed-in person on institution, hire, partner, train, platform surfaces sees it. Extra tabs only when `isOrgSurface(surface) && orgSlug && can(session,"manage_team")` (`OrgSettings.tsx:29`); otherwise the base capability alone. Both arms share it; the base `Settings` is `capabilities/account/Settings.tsx`.
- Heading: `B2CPageHeader` title "Settings" (`Settings.tsx:172`); tab strip aria-label "Settings" (:178). Platform surface instead uses "Settings" with description "Your own account: profile, sign-in and your data" (:155-156).
- Tabs (org surfaces): base `Profile`, `Preferences` (`settingsTabs.ts:20-21`; Payments and Referrals are train-only), then for managers `Organisation`, `Single sign-on`, `Provisioning` (`OrgSettings.tsx:36-38`). Opening tab is `organisation` when present, else `profile` (`Settings.tsx:34-35`); `?tab=` query selects a tab.
- Profile and Preferences panels are base capability (ProfilePanel, PreferencesPanel), owned elsewhere and not itemised here.
- Dialogs: unsaved-changes guard `LeaveConfirmModal` on a tab switch with a dirty profile: title "Leave without saving?", body "You have unsaved changes. If you leave now they will be lost.", buttons "Leave" (confirm) and Stay (cancel; default `LeaveConfirmModal.tsx:19-22`).

### Settings > Organisation tab (`OrgSettings.tsx:47-89`)
- Panel title "Organisation", description "The web address is fixed. Contact support to change it." (:76).
- Fields: Input "Name" (maxLength 200, :79); Input "Web address" read-only, value `/{slug}` (:80).
- Buttons: "Save name" / "Saving…" while busy (:83); disabled unless the trimmed name is non-empty and changed.
- States: loading/error AsyncBoundary default; failure Alert danger with the server message (:78). No toast; the form re-keys on the saved name.
- Gating: the api enforces manage_team; the tab is hidden otherwise.

### Settings > Single sign-on tab (`OrgSettings.tsx:97-134`, `ssoStatus.ts`)
- Panel "Single sign-on", description "OSCE Guide sets this up with you. Contact support to change it." (:102). Read-only; no buttons.
- Status badge + detail: "Not connected" / "People sign in with an email and password." (`ssoStatus.ts:10`); "Switched off" (warning) / "It is set up but switched off, so passwords are used." (:13); "Connected" (success) / `People can sign in with “{label}” or with a password.` or, when SSO-only, `Everyone signs in with “{label}”. Passwords are not accepted.` (:19-21; label default "single sign-on").
- Panel "Two-step sign-in for staff" (:117): text "Staff must confirm a code as well as a password." with Badge "Required", or "Staff sign in with a password alone." with Badge "Not required" (:122-127). Read-only.
- States: each panel its own AsyncBoundary (default loading/error).

### Settings > Provisioning tab (`ScimTokens.tsx`)
- Panel "Provisioning", description "Let your identity provider add and remove people here. Give each connector its own token." (:38-39).
- Fields: Input "Connector name" (:62). Buttons: "Create token" (submit, disabled when busy or blank, :64); per live token "Revoke" (secondary sm, :90); issued-token Alert warning "Copy this token now; it cannot be shown again. {token}" with button "Dismiss" (:45-47).
- Row: token label, meta `{prefix}… · last used {datetime}` or `never used` (:78); revoked token shows Badge "Revoked" (:82).
- States: empty "No tokens yet." (:70); loading/error default; failure Alert danger (:42).

## New organisation (public set-up request)
- Route: `/register/organisation` (`app/(auth)/register/organisation/page.tsx`, metadata title "Set up your organisation"); anonymous only (`RequireAnonymous`). `domains/assess/NewOrganisation.tsx`. Not under `[workspace]`; no permission, not arm-specific.
- Shell: eyebrow "For institutions", title "Set up your organisation", subtitle "Tell us about your programme or team. We create your organisation and make you its first admin, then you invite your faculty and trainees." (:100-102).
- Sections (FoldSection): 1 "Organisation", 2 "Purpose", 3 "Your account" (:111,124,150).
- Fields: Input "Organisation name" (required, :113); Select "Type" with options "Training programme", "Medical school", "Deanery", "Employer" (:25,114); checkbox group legend "What will you use OSCE Guide for?" (:127), hint "Tick at least one." (:128), options "Exam preparation", "Placement preparation", "Recruitment", "Onboarding", "Continuous development" (:18-22); helper "This decides which features your organisation gets. You can add more later in Settings." (:143); Input "Your name" (required); Input "Work email" (email, required); Textarea "Notes (optional)", hint "Anything we should know, such as cohort size, timelines or the exams you run." (max 1000, :168-169).
- Buttons: "Request set-up" / "Sending…" (`AuthButton`, :179); link "Sign in" after "Already set up?" (-> /login, :181-184).
- Validation: no purpose ticked on submit shows role=alert "Tick at least one." (:139).
- Error: Alert danger with the thrown message or "The request could not be sent. Try again." (:71,177).
- Success state: icon done, eyebrow "For institutions", title "Request received", subtitle `Thank you. We will set up {name} and email {email} with the next steps, usually within one working day.` (:84); link "Back to sign in" (-> /login, :88).
- Request filed: `POST /site/messages` kind contact, subject `Set up an organisation: {name}`, source "register/organisation" (`newOrganisationRequest.ts:19-22`); body lines Organisation, Type, Use, Contact, Notes. Literal "institutions", "faculty", "trainees", "organisation" (not vocabulary-driven).

## Reporting
- Route: `/app/[workspace]/reporting` (`app/app/[workspace]/reporting/page.tsx`, screen `reporting`, metadata "Reporting"); component `domains/assess/reporting/Reporting.tsx`, mapped `surfaces/assess/screens.tsx:130,246`. Nav item "Reporting" on the institution surface only (`surfaces/assess/surface.ts:45`); hire has no nav item but the screen exists. Gating is by the api (org reporting read); no client permission check.
- Note: `capabilities/attribution-dashboard` (DashboardFilterBar, Charts, presets, copy.ts) is NOT used by this screen. It is used only by `domains/partner/Dashboard.tsx` (partner surface), so it is inventoried with partner, not here.
- Heading: title "Reporting", subtitle "Each programme across all of its sittings. The pass rate counts decisions released to candidates." (:13-14; literal "sittings" and "candidates").
- Group eyebrow "Programmes" (:21); one row per programme: title = exam name, meta `{n} sittings · {n} candidates · {passRate}` (:26; literal "sittings", "candidates" even for one).
- Pass-rate label (`reporting/api.ts:13-15`): "Nothing released yet" when no pass_rate or zero released, else `{rate}% ({passed} of {released} released)`.
- No buttons, tabs, filters, row actions, dialogs or toasts.
- States: loading/error AsyncBoundary default; empty title "No programmes yet", description "Add a programme and hold a sitting to see figures here." (:19).

Screens: 18, controls: 330 (approximate: each quoted label, button, field, option, dialog and state string counted once)

<!-- parts/3-people-programmes.md -->
# Part 3: People, Team, Accept invitation, Programmes (baseline inventory)

Read-only inventory. Paths are under `web/src/` unless noted. `R` = `domains/assess/roster/`, `T` = `domains/assess/team/`.

## Vocabulary (`domains/assess/vocabulary.ts`, `useAssessWords.ts`)
`useAssessWords()` returns `assessWordsFor(useOptionalSurface()?.surface)`; hire surface gets EMPLOYER_WORDS, everything else INSTITUTION_WORDS (vocabulary.ts:46-48).

| key | Institution (vocabulary.ts:17-29) | Hire (vocabulary.ts:31-43) |
|---|---|---|
| sitting / sittings | "sitting" / "sittings" | "assessment" / "assessments" |
| Sitting / Sittings | "Sitting" / "Sittings" | "Assessment" / "Assessments" |
| trainee / trainees | "trainee" / "trainees" | "candidate" / "candidates" |
| Trainee / Trainees | "Trainee" / "Trainees" | "Candidate" / "Candidates" |
| People | "People" | "Candidates" |
| scheduleSitting | "Schedule a sitting" | "Schedule an assessment" |
| addPeople | "Add people" | "Add candidates" |

Everything else (cohort, group, programme, exam, station, "Team", "supervisor") is NOT vocab-driven and reads the same on both surfaces unless noted below. Noun-driven strings are marked **[w.X]** with their two renderings.

Permission: `can(session, "manage_team")` (`foundation/session/permissions.ts:11`) = `canManage`. Supervisors see Trainees without it; org admin/owner has it.

## Route: /app/[workspace]/trainees (Trainees = People page)
Route file `app/app/[workspace]/trainees/page.tsx:1-12`: metadata title "Trainees"; renders `<Screen name="trainees">`. Component `Trainees` in `R/Roster.tsx`. Who sees: any org member whose role reaches the screen (supervisor+); manage controls need `manage_team`.

### Header (R/Roster.tsx)
- Title: **[w.People]** = "People" / "Candidates" (Roster.tsx:44).
- Subtitle per tab (support.ts:98-117):
  - Everyone: "Everyone your organisation examines." (:105)
  - Add, 0 trainees: **[w.trainees]** `Add the ${trainees} who will sit your exams or training sessions.` (:108) -> "Add the trainees who will sit your exams or training sessions." / "Add the candidates who will sit ..."
  - Add, >0: `Add ${trainees} one at a time, or import a spreadsheet.` (:109)
  - Groups, 0 groups: `Sort ${trainees} into groups like intakes or rotation teams.` (:111)
  - Groups, >0: "Cohorts are an intake; groups are who you put on a circuit." (:113)
  - Access: `Give a ${trainee} access to an exam they can practise between ${sittings}.` (:115) -> "Give a trainee access to an exam they can practise between sittings." / "Give a candidate ... between assessments."
- Buttons: header action, only `canManage && section==="trainees"`: **[w.addPeople]** "Add people" / "Add candidates" (Roster.tsx:52), switches to Add tab.
- Hero (Everyone tab, total>0): title `${total} ${trainee|trainees}` + (when all pages loaded) ` across ${n} programme(s)` (Roster.tsx:136-140); detail `${sat} station(s) sat so far.` (:145), only when all loaded.
- Footer text (canManage only): "Looking for supervisors and admins? " + link "Go to the team" -> `/team` + "." (Roster.tsx:119-123).
- Load-more footer (Groups and Access tabs only, when more rows): `Showing ${rows} of ${total} ${trainees}.` (Roster.tsx:108) + LoadMore control.

### Tabs (TabStrip aria-label "Roster sections", Roster.tsx:69; labels support.ts:165-172)
- "Everyone" (with count badge = total) ; **[w.addPeople]** "Add people"/"Add candidates"; "Groups"; "Exam access" (canManage only).
- PeopleTabs (`domains/assess/PeopleTabs.tsx:22-30`, aria-label **[w.People]**): segmented "Trainees"/"Candidates" **[w.Trainees]** | "Team"; rendered only if `manage_team`; navigates to `/trainees` or `/team`.

### States (Roster.tsx)
- Loading/error of the whole lists: `AsyncBoundary` (foundation default copy, not in this folder).

## Tab: Everyone (R/TraineesPanel.tsx)
### Buttons
- "Invite everyone not signed in on this page (N)" (secondary sm; canManage and N>0) :435 -> bulk-resend invitations.
- Per-row checkbox column, header "Select", aria-label `Select ${name}` :255-260 (canManage only).
- Error retry button "Retry" :481.
- Bulk bar and row actions: see below.
### Fields
- Search input: placeholder `Search ${w.trainees}…` :414 ("Search trainees…" / "Search candidates…"), aria-label `Search ${w.trainees}` :415.
- Count eyebrow: `${n} trainee(s)` + "+" if more pages :402-403 (shown when rows>0 or query).
### Table columns (:255-343)
"Select" (canManage) | "Name" (name or email, email sub-line when named; initial avatar) | "Group" (`cohortName`: "No group" / "Unknown group", support.ts:24-25) | "Programme" (names joined ", " or "No programme" :317) | "Stations sat" | "Status" (badge) | "Actions".
Status badge text (support.ts:121-156): stages "Added", "Invited", "Accepted", "Member", "Booked"; attention overrides (warning badge): "Access revoked", "Added, no account yet", "Invited, not accepted", "Accepted, not a member".
### Dialogs (shared `Dialog` from `T/chrome.tsx`)
- Single action (TraineesPanel.tsx:517-562):
  - Delete: title `Delete ${name}?`; lead = `deleteLead` (support.ts:188-191): "You can only delete a trainee with no results recorded. If they have been examined, remove their access instead." or `${name} has sat N station(s), so deleting is likely to be refused once a result is decided. Revoke their access instead to keep their records.`; confirm "Delete"; busy "Deleting…"; tone danger.
  - Anonymise: title `Anonymise ${name}?`; lead `${name}'s name and email address will be scrubbed and their access revoked. Any decision already recorded about them is kept. This cannot be undone.` (:533); confirm "Anonymise"; busy "Anonymising…".
  - Revoke: title "Revoke access"; lead `${name} will not be able to sign in or sit anything, and stays on the roster with their results intact.` (:535); confirm "Revoke access"; busy "Revoking…".
  - Restore: title "Restore access"; lead `${name} will be able to sign in and sit again.` (:536); confirm "Restore access"; busy "Restoring…" (commit tone).
  - Cancel label: from `Dialog` (see Team chrome section).
- Bulk revoke (:564-581): title `Revoke access for ${n} person|people?`; lead "They will not be able to sign in or sit anything, and stay on the roster with their results intact."; confirm "Revoke access"; busy "Revoking…".
- TraineeEditDialog: see its section.
### States
- Loading: `Loading ${w.trainees}…` role=status :488.
- Empty (no query): EmptyState title `No ${w.trainees} yet`, description `Add ${w.trainees} so you can put them on an exam or training circuit.` :497-498.
- Empty (search): `No ${w.trainees} match “${query}”.` :493.
- Error: danger Alert with the error message + "Retry" :473-483.
- Not canManage footer: "Contact an owner or admin to change who has access." :513.
### Toasts / notices (Alert above the filter bar, tones success/warning/danger)
- Delete: `Removed ${name} from the roster.` :176
- Anonymise: `${name}’s name and email address have been removed. Any results already recorded are kept.` :182
- Revoke / restore: `Revoked access for ${name}.` / `Restored access for ${name}.` :190-191
- Delete refused (`trainee_in_use`, shown in dialog): `${name} has a decision recorded and cannot be deleted. Revoke their access instead.` :200
- Resend ok: `Emailed ${email} a link to choose a password for ${invited_to}.` :227
- Resend `invitation_not_pending` (warning): `${name}  has already set up their account, so there is no invitation to resend.` :235
- Resend other: `rosterErrorMessage` -> `${email} is already on this roster.` for `trainee_exists` (support.ts:196) else generic error message.
- Bulk results: `bulkSummary` (support.ts:58-70) e.g. "Sent 2 of 4 invitations. 1 already signed in."; "Updated N of M people."; "Revoked N of M people."; failure shows the error message danger.

### Bulk bar (R/TraineeBulkBar.tsx; canManage and rows>0)
- Checkbox label: "Select all on this page" :43.
- When any ticked: "N selected" :47; buttons "Resend invitations" :49, "Revoke access" :70; link-button "Clear" :73.
- Select (aria-label "Move to group" :52): options "Move to group…" :61, "No group" :62, then each cohort name.

### Row actions (R/TraineeRowActions.tsx; whole cell hidden unless canManage :45)
- "Edit" (title "Change their name, email or cohort.") :61
- "Send invitation" (row has no account, user_id null) or "Resend invitation" :50, busy "Sending…" :83; title "Email them a fresh link to set up their account." :80. Shown only if `invitationResendable` (access active, email has "@", invitation pending or no account).
- "Already joined" (disabled; after `invitation_not_pending`) title "That person has already set up their account, so there is no invitation to resend." :70-72
- "Revoke" / "Restore" titles "Stop them sitting or signing in. Their records are kept." / "Let them sit and sign in again." :93-98
- "Delete" (danger) title "Remove them from the roster. Refused once a result is decided." :104-107
- "Anonymise" title "Erase their personal details but keep the results." :118-121; or disabled "Anonymised" title "Already anonymised" :110-111.

## Dialog: Edit trainee (R/TraineeEditDialog.tsx)
- Title "Edit trainee" :100 (not vocab-driven, same on hire). Lead: "Only what is on this form is written. The email address cannot be changed here, because it keeps this person’s results linked to them." :101
- Static: label "Member" with the email :110-111.
- Fields: "First name" :120, "Last name" :135, "Cohort" :152 with hint "An intake. Choose an existing one; cohorts are created under Groups." :155; select options "No cohort" :163 + cohort names.
- Info alert if no cohorts: "No cohorts in the organisation yet. Create one under Groups, then come back to set it here." :172
- Buttons: "Cancel" (chrome.tsx:119), "Save" / "Saving…" :104-105.
- Error: `stale_revision` -> "Someone else changed this person just now. We have reloaded the list: close this and choose Edit again to see their changes." :88; else generic message.

## Shared chrome (T/chrome.tsx)
- `TabStrip` role=tablist, tab buttons with optional count (:41-73).
- `Dialog`: title, optional lead, optional children, inline danger Alert for error, "Cancel" (:119), commit label / busy label; Esc/overlay close disabled while busy (:107). Commit tone "commit" or "danger".
- `formatWhen`: "None" when absent (:132), else short date-time.

## Tab: Add people / Add candidates (R/AddTraineePanel.tsx)
Tab label **[w.addPeople]**. Visible to all roster viewers but the content is gated on `canManage`.
- Not canManage: info Alert title `Only an owner or admin can add ${w.trainees}` :89 ("...add trainees" / "...add candidates"), body "Ask one of them to add the people you need on the roster." :90
### Panel "Add one person" :98
- Description: "They are invited by email. If they have no account yet, we create one and send them a link to choose a password. If that email cannot reach them, set a temporary password to relay by hand." :99
- Fields: "Full name" :113 placeholder "e.g. Amina Khan" :120 (split on last space into first/last name, splitName :14-22); "Email address" :130 (type=email, required) placeholder "amina@hospital.nhs.uk" :139; "Cohort (optional)" :149 hint `An intake, such as "June 2026". Cohorts are created under Groups.` :152; select options "No cohort" :160 + cohort names.
- Temporary password field (`foundation/ui/TemporaryPassword.tsx`): checkbox "Set a temporary password instead of emailing a link" (:67 there); label "Temporary password" (:24), hint `At least ${MIN_LENGTH} characters, mixing letters with numbers, punctuation or capitals.` (:25); button "Generate".
- Submit button: **[w.trainee]** `Add ${w.trainee}` :189 ("Add trainee" / "Add candidate"), busy "Saving…"; disabled until email typed and password ready.
- Issued password Alert: title `Password for ${email}` with "Copy"/"Copied" and a dismiss button (TemporaryPassword.tsx:109-118).
### Panel "Import a spreadsheet" :195
- Description: `Upload a list of ${w.trainees} saved from Excel or Google Sheets as a .csv file. Anyone already on the list is skipped and shown to you.` :196
- Button "Import from spreadsheet" :199 (opens BulkImportDialog).
### Toasts / alerts
- Success: `${email} is on the roster.` :74; with typed password but pre-existing account: `${email} is on the roster. They already had an account, so the password you typed was not used.` :73
- Error: `rosterErrorMessage` (`${email} is already on this roster.` for trainee_exists, else generic).

## Dialog: Import trainees (R/BulkImportDialog.tsx + ImportParts.tsx)
- Title **[w.trainees]** `Import ${w.trainees}` :154 ("Import trainees" / "Import candidates"); lead `One spreadsheet of ${w.trainees}, saved as .csv. The first row must name the columns.` :155
- Instructions (ImportParts.tsx): "Required column" :16 `email`. Their email address; "Optional columns" :22 `firstName`, `lastName`, or one `name` column. Their name; `cohort` or `group`. The name of a cohort that already exists here (e.g. "June 2026"); "Example" :35 with `email,firstName,lastName,cohort / amina@hospital.nhs.uk,Amina,Khan,June 2026`.
- Dropzone (csv only, single): "Drop your .csv here, or choose a file" :184 (file name once chosen); ".csv files only" :187 (or `N.N KB`).
- Parse messages (csv.ts): "That file is empty." :134; `The first row must name the columns, and one of them must be \`email\` (found: ...).` :141; "No rows in that file had an email address." :189.
- Preview: `N row(s) ready to import.` :198; "No email address on line(s) X, so those rows are left out." :203; "Line(s) X: not a valid email address, so that row is / those rows are left out." :210; "Line(s) X: the address already appears earlier in the file, so it is / they are counted once." :220.
- Unknown cohorts: "No cohort here is called A, B." :229; checkbox `Create that cohort / those cohorts when importing` :231; "Otherwise those people are added with no cohort." :236.
- Buttons: Cancel (chrome); commit labels: `Import N trainee(s)`/`Import ${w.trainees}`/"Done" :158-164; busy "Importing…" :165.
- Result: alert `${n} added, ${m} skipped.` (ImportParts.tsx:58); "Not imported" :62 list `${email}: ${reason}`; reasons (csv.ts:196-203): "already on the roster", "not a usable email address", else code with underscores replaced by spaces.

## Tab: Groups (R/GroupsPanel.tsx, CohortsPanel.tsx, GroupEditDialogs.tsx)
Tab label "Groups". Page shows the Cohorts panel then the Groups panel. Mutating controls only when `canManage`. Panel errors appear as danger Alerts.
### Panel "Cohorts" (CohortsPanel.tsx:72)
- Description: "An intake, such as a start date. Each trainee can be in one cohort, chosen when they are added." :73
- Empty: "No cohorts yet. Create one below, or leave people without." :83
- List aria-label "Cohorts" :86; each row: name, and `academic_year` or `status` caption :97.
- Row actions (canManage): "Rename" :107, "Delete" :115.
- Fold "Create a cohort" :127 with inputs aria-label "Cohort name" placeholder "e.g. June 2026 intake" :130-134; aria-label "Academic year" placeholder "2026/27" :138-142; button "Create cohort" / busy "Working…" :151.
### Panel "Groups" (GroupsPanel.tsx:87)
- Description: "A named list of people you can add to a circuit together, such as a rotation team or a resit group. A person can be in more than one." :88
- Empty: "No groups yet. Create one below and choose who is in it." :92
- List aria-label "Trainee groups" :95 (not vocab-driven); row: label, `${n} person|people` :106.
- Row actions (canManage): "People" :116 (opens members dialog), "Rename" :124, "Delete" :132.
- Fold "Create a group" :145, description "Everyone in your organisation sees the same group names." :146; input aria-label "New group name" placeholder "e.g. Tuesday rotation" :150-154; button "Create group" / "Working…" :163.
### Dialogs (GroupEditDialogs.tsx)
- Rename group: title "Rename group" :86; lead `Everyone still in “${name}” stays in it. Only the name changes.` :87; label "New name" :101; buttons "Rename"/"Saving…" :90-91 + Cancel.
- Delete group: title "Delete group?" :188 (danger); lead empty: `Delete “${label}”? It has nobody in it, so nothing else changes. This cannot be undone.` :191; with members: `Delete “${label}”? It still has N people in it, and a group is not deleted while it does. Empty it from People first.` :192; commit "Delete group"/"Deleting…" :196-197 (disabled while member_count>0); error `group_not_empty`: `${serverMessage} Open People, untick everybody and save, then delete it.` :174.

### Dialogs (R/CohortEditDialogs.tsx)
- Rename cohort: title "Rename cohort" :84; lead "Everyone in this intake stays in it. Only the name changes." :85; labels "New name" :99, "Academic year" :114 with hint "Leave blank to take the year off this intake." :117, placeholder "2026/27" :124; buttons "Save"/"Saving…" :88-89 + Cancel.
- Delete cohort (danger): title "Delete cohort" :204; lead = `cohortDeleteLead` (support.ts:175-183): `Delete “${name}”? Nobody can be put into it afterwards. This cannot be undone, and a cohort that still has trainees in it is not deleted. ` + ("No sittings are held for it." | `The N sitting(s) held for it is/are kept but no longer belong to any cohort.`) [sitting hard-coded, not vocab]; commit "Delete cohort"/"Deleting…" :208-209; error `cohort_in_use`: `${serverMessage} Move them onto another intake from their row on the Trainees tab first.` :190.

## Dialog: People in {group} (R/GroupMembersDialog.tsx)
- Title `People in ${group.label}` :52; lead "Tick everyone who belongs to this group. Saving replaces the current list." :54
- Loading/error: `AsyncBoundary` default.
- Empty roster: info Alert "Nobody is on the roster yet, so there is nobody to put in a group." :118
- Count: `${picked} of ${total} selected.` ; checkbox list of roster rows (name, right-aligned email), sorted active first by name.
- Buttons: "Cancel", "Save group" / "Saving…" :151. Error: danger Alert.
- Note: list covers only the roster rows loaded so far (Roster.tsx passes `trainees.rows`).

## Tab: Exam access (R/AccessPanel.tsx; only rendered tab when `canManage`)
- Panel "Grant exam access" :105 (canManage); description **[w.trainees, w.sittings]** `Lets ${trainees} practise between ${sittings}. They do not need it to take an exam they are booked on.` :106 ("...Lets trainees practise between sittings..." / "Lets candidates practise between assessments...").
- Fields: "Who" :121 select, first option **[w.trainee]** `Choose a ${trainee}…` :129 then roster people; "Exam" :143 select, first option "Choose…" :151 then exam names; "Until (optional)" :164 (date).
- Button "Grant access" / "Granting…" :181.
- Search: label "Search grants" :190 (sr), input type=search placeholder "Search by person or exam…" :197.
- Table columns (GrantsTable :269-305): "Who" (name or "Not on this roster"), "Exam" (code), "Status" ("Live" | "Revoked" | "Expired"), "From", "Until" ("No end date"), "Actions": "Revoke" (canManage and live).
- States: loading/error via `AsyncBoundary`; empty (no query) **[w.Trainees]** `No practice access given yet. ${Trainees} can still take every exam they are booked on.` :206; empty with search: table empty title "No grants match." :325.
- Toasts: success `${email} can now practise ${examCode}.` :78; errors shown as danger Alert (generic message).

## Route: /app/[workspace]/team (Team)
Route file `app/app/[workspace]/team/page.tsx`: metadata title "Team"; `<Screen name="team">`; component `Team` (T/Team.tsx). Visible to people with `manage_team` (hire nav: `surfaces/hire/surface.ts:28` label "Team"; People menu also holds Trainees via `PeopleTabs`). Page strings are NOT vocab-driven (identical on hire).
- Title "Team" :41. Subtitle per tab (T/support.ts:44-52): Members "Who can run circuits and sign off results in this organisation." :47; Add people "Invite a supervisor or an admin by email." :49; History "Who added, changed, or removed people and groups." :51.
- Header button (canManage and Members tab): "Add people" :46.
- Tabs (TabStrip aria-label "Team sections" :52): "Members", "Add people", "History" (Team.tsx:16-18).
- Footer: "Looking for the people being examined? " + link "Go to the roster" -> `/trainees` + "." :65-66 (hard-coded "roster", "people being examined").

### Tab: Members (T/MembersPanel.tsx)
- Search: placeholder "Search staff…" :218, aria-label "Search staff" :219; count eyebrow `${n} staff account(s)` + "+" (support.ts:40).
- Filter-bar button (canManage and any awaiting): "Resend invitations (N)" / "Resending…" :229.
- Columns: "Email" (or "No email address on file" + short id; "Invited" tag when pending) :136-150; "Role" (Owner/Admin/Supervisor/...) :156; "Circuits led" :163; "Access" (badge "Active" / "Revoked") :172-178; "Actions" (canManage) :182.
- Row actions (RowActions :344): "Resend invitation" / "Resending…" (not owner, active, invited; title "Only sent if that person has not set up their account yet.") :364-367; "Change role" (not owner) :377; "Revoke" (active; disabled for owner, title "An organisation's owner cannot be revoked here") :389-392; "Restore" (revoked) :401.
- Dialogs: 
  - Change role: title "Change role" :274; lead `${email|"This person"}'s role in this organisation.` :275; label "Their role" :288; hint = ROLE_DESCRIPTIONS.supervisor + admin ("Runs circuits and marks the candidates on them. Manages the team and the organisation's settings, and signs off results.", roles.ts:21-27); select options "Supervisor", "Admin" (ASSIGNABLE_ROLES); commit "Save role"/"Saving…" :278-279.
  - Revoke access (danger): title "Revoke access" :310; lead `${email|"This person"} will lose access to this organisation. Nothing they have marked is deleted.` :313; commit "Revoke access"/"Revoking…".
  - Restore access: title "Restore access" :327; lead `${email|"This person"} will be able to sign in to this organisation again, with the role they had.` :330; commit "Restore access"/"Restoring…".
  - All with Cancel.
- States: loading "Loading staff…" :245; empty EmptyState title "No staff yet", description "Invite a supervisor so somebody can run a circuit." :252-253; empty with search `No staff match “${query}”.` :249; error danger Alert + "Retry" :234-240; non-manager footer "Contact an owner or admin to change who has access." :268.
- Toasts (success Alert above filter bar): `Resent ${sent} of ${n} invitations.` :81; `Resent the invitation to ${email}.` :94; `${email|"this person"} is now ${role lowercased}.` :116; `Revoked access for ${who}.` :119; `Restored access for ${who}.` :122; failures as danger Alert (generic message) when no dialog is open.

### Tab: Add people (T/InvitePanel.tsx)
- Not canManage: info Alert title "Only an owner or admin can invite staff" :76, body "Ask one of them to add the person you need." :77.
- Panel "Invite someone to the team" :85, description "Supervisors run circuits and mark them. Admins also manage the team and sign off results." :86.
- Fields: "Email address" :100 with hint "If they have no account yet we create one and email them a link to choose a password." :103, placeholder "supervisor@hospital.nhs.uk" :112; "Their role" :122 with hint = ROLE_DESCRIPTIONS[role] :124, options "Supervisor"/"Admin"; temporary-password field (same as roster: "Set a temporary password instead of emailing a link", "Temporary password", "Generate", hint).
- Submit: "Add person" / "Inviting…" :164 (disabled until email and password ready).
- Results: success `Invited ${email}. They have been emailed a link to choose a password.` :151 or `${email} already had an account and is now ${role} here.` :152; issued-password Alert `Password for ${email}` (Copy/Copied/dismiss); error danger Alert.
- Panel "Import a spreadsheet" :170, description "Upload a list of staff saved from Excel or Google Sheets as a .csv file. Anyone already on the team is skipped and shown to you." :171; button "Import from spreadsheet" :174.

### Dialog: Import staff (T/BulkInviteDialog.tsx, T/csv.ts)
- Title "Import staff" :97; lead "One spreadsheet of supervisors and admins, saved as .csv. The first row must name the columns." :98; commit "Invite N person|people" / "Import staff" / "Done" :102, busy "Importing…" :104.
- Instructions: "Required columns" :167 (`email`. Their email address; `role`. Either `supervisor` or `admin`); "Example" :180 (`email,role / supervisor@hospital.nhs.uk,supervisor / admin@hospital.nhs.uk,admin`).
- Dropzone: "Drop your .csv here, or choose a file" :121; ".csv files only" :124.
- Parse errors (csv.ts): "The first row must name the columns, and one of them must be `email`." :83; "No row in that file had an address and a role we can grant." :~126; `That file has N people. One upload takes 500 at most, so split it into smaller sheets.` :136.
- Preview: `N row(s) ready to import.` :133; skipped-lines / invalid-lines notes as in roster import :137-145; badRoles: "Line(s) X named a role this organisation cannot give. Only supervisor or admin can be invited, so those rows are left out." :149-152.
- Outcome: `${n} added, ${m} skipped.` :199; `${k} person was / people were emailed a link to choose a password. They cannot sign in until they use it.` :203; "Not imported" :209 list with reasons (csv.ts:145-154): "already on the team with that role", "no account to invite at that address", "not a usable email address", else code with spaces.

### Tab: History (T/ActivityPanel.tsx)
- Filter form: inputs "Done by" (email, placeholder "name@hospital.nhs.uk") :42-44, "Action" (placeholder "e.g. membership.") :49-51; buttons "Filter" :55, "Clear" (only when filtering) :67.
- Rows: summary or action key; timestamp; "By ${actor_email}" :103.
- States: loading/error via `AsyncBoundary` default; empty (filtered) title "Nothing matches those filters." description "Try a different address or action." :78-79; empty (unfiltered) title "Nothing here yet." description "Invitations, role changes and roster edits appear here as they happen." :82-84.

## Route: /accept-invitation (access route, `app/(auth)/accept-invitation/page.tsx`)
Metadata title "Accept your invitation". Renders `<ResetPassword invitation />` inside Suspense (fallback null). Public (no session); reached from the invitation email's token link. Strings live in `capabilities/account` ResetPassword (see below).

#### Accept invitation screen strings (`capabilities/account/ResetPassword.tsx` with `invitation`; errors `support/mapAuthApiError.ts`)
- Split-layout card, icon "mail", eyebrow "Invitation" :168, title "Accept your invitation" :169, subtitle "Choose a password to finish setting up your account." :171.
- Fields: "Password" :176 (hint `PASSWORD_HINT`), show/hide toggle aria-label "Show password" / "Hide password" :157; "Confirm password" :188. Both autocomplete new-password, required.
- Button: "Accept invitation" / "Saving…" :210.
- No token in URL: card icon warning, title "That link is incomplete", subtitle "Use the link in your invitation email. If you already chose a password, sign in; otherwise ask whoever invited you to send it again." :113-114; link "Sign in" -> /login :120.
- Success (not auto-signed-in): title "Your account is ready" :133; subtitle "Sign in with the password you just chose." :141 (or "Password saved" + "We saved it but could not sign you in just now. Sign in with the password you just chose." when sign-in failed; or "Your account asks for a second step, so sign in to finish with your authenticator."); button "Sign in" -> /login. On auto sign-in success: redirects to /app.
- Errors: `invalid_reset_token`: "That invitation has already been used or has expired. If you already chose a password, sign in. Otherwise ask the person who invited you to send it again." (mapAuthApiError.ts:59) plus "Sign in" link; generic fallback "We couldn't save your password. Please try again."; field errors from `resetPasswordSchema` (password rules / mismatch).

## Route: /app/[workspace]/programmes (Programmes screen)
Route file `app/app/[workspace]/programmes/page.tsx`: metadata title "Programmes"; `<Screen name="programmes">` renders `domains/assess/programmes/Programmes.tsx`. Nav: `surfaces/assess/surface.ts:49` label "Programmes", gated on permission `author_content`. Not shown in the hire nav (hire's Build covers it: the Programmes tab is inside Authoring for any org scope, `supportsProgrammes`, api/scope.ts:59). Write controls gated `schedule_sittings`.

### Header (Programmes.tsx:21-24)
- Title "Programmes"; subtitle "A programme is an exam you run sittings against. Adopt one the platform publishes or add your own, activate it, and it is offered when you schedule a sitting." (hard-coded "sittings"/"sitting", NOT vocab-driven, same on hire).

### Section: Exams the platform publishes (domains/assess/programmes/PlatformExams.tsx)
Hidden entirely when the catalogue is empty (:45). Loading/error via `AsyncBoundary`.
- Eyebrow "Exams the platform publishes" :48.
- Row: title = exam title; meta `${code} · ${n} library station(s)` :53; trailing "Adopted" badge (already imported) or, with `schedule_sittings`, button "Adopt" / "Adopting…" :65.
- Toasts: success `${title} is now one of your programmes. Schedule a sitting against it whenever you are ready.` :29; `unknown_exam`: "The platform no longer offers that exam. The list has been refreshed." (support.ts:6); else generic error. Danger/success Alert above the list.

### Section: Programmes list (`capabilities/authoring/sections/ProgrammesSection.tsx`, also the "Programmes" tab of Authoring)
- Lead text: "A programme groups this institution's sittings under one exam." :66 (hard-coded).
- Button (only `schedule_sittings`): "New programme" :61.
- Card header: "Programmes" + count (ListCard countLabel :73).
- Row: icon, title = exam name, meta `${exam_code} · ${source}` + " · OSCE Guide exam" for platform-owned :99; `StatusBadge`: "Published"/"Active"/"Draft"/"Retired"/"Archived" (parts/StatusPills.tsx:55-61).
- Row action (icon button with tooltip label): "Retire" (active) / "Activate" (draft) / "Reactivate" (retired) :85, busy "Saving…" :107; sets status "retired" or "active".
- Dialog "Add programme" :129: lead "Choose the exam. Sittings you schedule for it are grouped under this programme." :130; label "Exam" :146; select first option "Select an exam…" :153, then `${name} (${code})` for published exams only; hint "Only published exams are listed." :165 or (none published) "Publish an exam to use it here." :163; exams load failure `Exams could not be loaded: ${message}` with retry :161; buttons Cancel (AuthoringDialog) and "Add programme" / "Adding…" :133-134 (disabled until exam chosen).
- States: loading skeleton (ListCard B2CSkeleton 3 lines); empty title "No programmes yet", description "Add a programme for each exam you run sittings against." :78-79 (non-authors see the shared READER_EMPTY_TEXT instead of the description); error Alert with "Dismiss" button that reloads (ListCard :40, onDismissError=reload).
- Toast/alert: failures as danger Alert above list (`action.error`); no success toast.

Screens: 12, controls: 424

<!-- parts/4-authoring-stations.md -->
# Part 4: Build hub (authoring): marking schemes, exams, templates, stations (baseline inventory)

Read-only inventory. Paths under `web/src/`; `A` = `capabilities/authoring/`; `P` = `A/parts/`; `S` = `A/sections/`.

## Vocabulary
`useAssessWords` is NOT used anywhere under `capabilities/authoring`. Every string here is hard-coded and identical on institution and hire surfaces (hire's nav label is "Build" too, `surfaces/hire/surface.ts:29`; institution `surfaces/assess/surface.ts:47`). Exceptions: sitting words appear as literals ("sittings", "sitting"). For reference the vocab pairs are: sitting/assessment, trainee/candidate, People/Candidates, Add people/Add candidates, Schedule a sitting/Schedule an assessment (`domains/assess/vocabulary.ts:17-43`).

## Permission model (shared by every authoring screen)
- Capability manifest `A/capability.ts:23-31`: id "authoring", title "Authoring", surfaces assess, hire, partner, platform; permission any of `run_circuits` or `administer_platform`; path `/authoring`; hidden from staff nav on assess and hire (they use their own Build entry).
- Read access: anyone passing the capability gate. Write controls: `can(session,"author_content")` via `A/hooks/useCanAuthor.ts`; `AuthoringButton write` / `AuthoringIconAction write` / `AuthoringSectionLead action` render nothing without it (P/AuthoringButton.tsx, P/AuthoringSectionLead.tsx).
- Non-authors see `READER_EMPTY_TEXT` = "Nothing here yet." (P/CannotAuthor.tsx:4) instead of an empty-state description (unless `sameForReaders`); `CannotAuthor` Alert (warning): "Only an organisation administrator can edit this." (P/CannotAuthor.tsx:8).
- Platform-owned rows (`owner_kind === "platform"`) are read-only in an org scope (`canManageTemplate`, S/versions.ts:36).
- Scope: `useAuthoringScope()` = org scope in a workspace, platform scope on the staff console. Programmes tab only for org scope (`supportsProgrammes`, A/api/scope.ts:59).

## Shared parts (strings reused on every screen)
- ListCard (P/ListCard.tsx): header `${countLabel} ${count}`; loading = skeleton; error Alert with "Dismiss" button (reloads) :40; empty = EmptyState (title, description or READER_EMPTY_TEXT).
- StatusBadge (P/StatusPills.tsx:55-61): "Published", "Active", "Draft", "Retired", "Archived" (unknown -> "Draft").
- PublishStatusLine (P/StatusPills.tsx:12-48): optional kind badge; "Live · v{n}" or "Not live"; "Draft · v{n}"; "Archived only".
- AuthoringDialog (P/AuthoringDialog.tsx): title, lead, children, inline error, "Cancel" + commit button (label/busyLabel per caller).
- ConfirmModal (foundation): default buttons "Cancel" and `confirmText` (default "Confirm").
- AuthoringIconAction: icon-only button with tooltip = `label`; shows `busyLabel` while busy.
- LoadError (P/LoadError.tsx): message + "Retry" underline button.
- AuthoringCatalogFilterBar (P/AuthoringCatalogFilterBar.tsx): select aria-label "Filter by exam" with options "All exams" / "Loading exams…" / "Exams unavailable" + one per exam; optional select aria-label "Filter by status" with options "Active", "Archived", "All" (P/stationListUrl.ts:6-8); search input (placeholder/aria per caller, default "Search…" / "Search catalogue").
- Stale write: "Someone else changed this {what} just now. We have reloaded it with their changes; make your edit again." (A/api/stale.ts:12).

## Route: /app/[workspace]/authoring (Build hub)
- `app/app/[workspace]/authoring/page.tsx`: redirects to `/app/{workspace}/authoring/rubrics`. `[section]/page.tsx`: metadata title "Authoring"; renders `<AuthoringHome section>` inside `<Capability id="authoring">`. Unknown/missing section redirects to `rubrics` (A/Authoring.tsx:35-43).
- Header (institution/hire; A/Authoring.tsx:90): title "Authoring", subtitle "Marking schemes, exams, programmes, templates and stations." (platform surface uses `PlatformTabbedScreen` with same title/description :78-79).
- Tabs (aria-label "Authoring section", `A/sections.ts:5-11`): "Marking schemes" (rubrics, default), "Exams", "Programmes" (org scope only), "Templates" (station-templates), "Stations". Tabs navigate to `/authoring/{id}`.
- Other routes under authoring: `feedback-templates/new` and `feedback-templates/[templateId]/versions/[version]` are legacy redirects to `../rubrics` (feedback templates were merged into rubric versions as `marking_layout`). No feedback-template screens exist.

## Tab: Marking schemes (S/RubricsSection.tsx; route /authoring/rubrics)
### Buttons
- "Create marking scheme" (commit, plus icon; author only) :84 -> `/authoring/rubrics/new`.
- "Load more marking schemes" / "Loading…" :156 (when more pages).
- Row: whole row opens detail; icon action "Open versions" :132.
### Tabs and filters
- Lead text: "The marking structure a station is assessed against." :88
- Filter bar: exam select (aria "Filter by exam"), search placeholder "Search marking schemes…" :96, aria-label "Search marking schemes" :97.
### Row content
- Title = rubric title; PublishStatusLine with kind badge "OSCE Guide" for platform-owned.
### States
- Card header "Marking schemes N" :104; loading skeleton; empty title "No marking schemes", description "Create a marking scheme, publish a version, then build exams and templates on it." :109-110; error Alert + "Dismiss"; more-pages error "Could not load more rubrics: {message}" :145.
- Action error: danger Alert.

## Screen: Marking scheme versions (S/RubricDetail.tsx; inline view inside the Marking schemes tab)
### Buttons
- Back button "Marking schemes" :52.
- "New draft version" / "Creating…" (author only) :69.
- Per version icon actions: "Edit in the builder" (draft and author) / "Open in the builder" :107 -> `/authoring/rubrics/{id}/versions/{n}`; "Publish" (draft) busy "Publishing…" :116-118; "Archive" (published) busy "Archiving…" :133-135. Publish/archive hidden for platform-owned in an org scope.
### Content
- Heading = scheme title :61; per version "Version {n}" :96, system prompt excerpt or "No system prompt." :99; StatusBadge.
### Dialogs
- Archive: ConfirmModal title "Archive this version?" :168; message `Version {n} stops being used to mark new attempts. If it is the current version, the newest other published version takes over. It is refused while an exam or an upcoming sitting still uses it.` :170; confirm "Yes, archive" :169; Cancel; error inline.
### States
- Empty (author): "This marking scheme has no versions yet. Cut a draft to start writing it." :77; non-author: "Nothing here yet."; loading/error via `AsyncBoundary`; action error danger Alert.

## Tab: Exams (S/ExamsSection.tsx; route /authoring/exams)
### Buttons / filters
- Checkbox "Drafts only" :72.
- "Create exam" (author; plus icon) :86.
### Row
- Title = exam name; meta `${code} · ${n} min reading · ${n} min station` + " · OSCE Guide" (platform-owned) + " · partner pilot" :113; StatusBadge.
- Icon actions (author): "Edit" (or tooltip "OSCE Guide exams are edited in the staff catalogue" when locked, disabled) :118-121; "Publish" (draft; tooltip "Choose a marking scheme version first" when none; busy "Publishing…") :145-147; "Retire" (published, not locked) :160; "Delete" (not locked, not platform scope) :171.
### Dialogs
- Create exam: AuthoringDialog title "Create exam" :186; lead "The code is unique within this organisation only, so two schools may both have a finals." :187; fields = ExamFields (below); commit "Create exam" / "Creating…" :190-191 (disabled until code and name).
- Edit exam: title "Edit exam" :215; lead "Publishing is refused without a marking scheme version." :216; step guide (`examSteps`/`examNextAction`, S/examSteps.ts): steps "Pick marking scheme" (note "Chosen"/"Not chosen"), "Publish" (note "Draft"/"Live"/"Retired"); line one of "Retired. It is no longer offered for new sittings." / "Live. Add a programme for it so people can take it." / "Pick a marking scheme, then publish." / "Publish this exam to run sittings against it."; code field disabled; commit "Save" / "Saving…" :218-219.
- Delete: ConfirmModal title `Delete "${name}"?` :267; message "Only a draft nothing was ever built on can be deleted this way. Anything with a station, a sitting or an attempt against it cannot be deleted. Retire it instead." :270; confirm "Delete exam".
- Retire: title `Retire "${name}"?` :284; message "It stops being offered for new practice and sittings, and cannot be published again. What was already attempted against it stays as it is." :287; confirm "Retire exam".
### States
- Card header "Exams N" :94; empty (all) title "No exams yet", description "Create an exam, attach a marking scheme version, then publish it to run sittings against it." :99-102; empty (drafts only) title "No draft exams", description "Everything here is published. Clear the filter to see the whole catalogue." (same for readers); error Alert + "Dismiss"; action error danger Alert; stale edit error text (staleRefusal "exam").

## Fields: exam form (S/ExamFields.tsx, S/ExamSettingsFields.tsx)
- "Code" placeholder "e.g. finals" :94-100 (disabled when editing); "Name" placeholder "e.g. Final MB OSCE" :103-108; "Reading time (seconds)" :111 (default 120); "Station time (seconds)" :119 (default 600); "Attempts per station" :127 (default 3).
- "Marking scheme version" select :135: first option "None yet" or "Marking schemes could not be loaded" :141; options `${scheme title} · v${n}` (latest published per scheme, plus the currently chosen); load error shows LoadError with Retry :148.
- Fold "Exam settings" (collapsed) :66: "Date label" (max 40, placeholder "Exam date") :68-74; group "After a station" with "Tutor debrief", "Practise as the patient" :10-11,78; group "Help dock" with "Find screens", "Answer from the knowledge base" :14-15,89; group "Other" with "Show examiner tips while marking" :101, "Email people waiting for a peer partner" :107; textareas "Station writing prompt", "Condition summary prompt", "Blog prompt" (max 20000, 4 rows) placeholder `Blank uses the built-in prompt (${key or "generic.station"|"generic.summary"|"generic.blog"}).` :26,31,34,121.
- Partner pilot: checkbox "Partner pilot" (platform scope only) :164; else note "Partner-pilot status is set by OSCE Guide staff, not from here." :169.
- Defaults (ExamFields.tsx:31-38): date label "Exam date", session modes debrief + practice_as_patient, help modes navigate.

## Tab: Stations (S/StationsSection.tsx, S/StationsTable.tsx; route /authoring/stations, deep link `?station={id}&status=`)
Permission: read for all; "Import from PDF or Word" and "New station" are `AuthoringButton write` (author_content); Approve/Withdraw approval only on platform scope for platform admins; Archive is author-only.
### Buttons
- "Import from PDF or Word" (secondary) StationsSection:141 opens ImportStationDialog.
- "New station" (commit) :150 -> `/authoring/stations/new`.
- Lead: "Published station cases for sessions and practice." :155 plus count `{n}{+} station(s)` and ` · {n} template(s) available` :158-160.
- Retry (inline button in error Alert) :181.
### Filters
- Exam select aria "Filter by exam"; status select aria "Filter by status" (Active/Archived/All); search placeholder "Search stations by name…" :172, aria "Search stations" :173.
### Table columns (StationsTable.tsx)
- "Station name" :67 (title button opens detail), "Exam" :81 (code uppercased), "Status" :90 (StatusBadge + pill "Approved" / "Awaiting approval" :39, published only), "Used by" :100, "Created at" :108 (en-GB date, "-" when missing), "Actions" :117.
- Row actions (tooltips): "Approve" / "Withdraw approval" (busy "Approving…" / "Withdrawing…") :130-132 (platform admin only); "Archive" (published; busy "Archiving…") :147-149; "Open versions" :156.
### Dialog
- Archive ConfirmModal: title `Archive "{title}" (v{n})?` or "Archive station?" :242; confirm "Archive" :245; body StationUsedBy list then "Past attempts stay intact. The station is removed from the live library." :252; Cancel.
### States
- Loading skeleton; empty with search: title "No matching stations", description "Try a different name, or clear the exam filter." :175; empty reader: "No stations yet" / "Nothing here yet." :177; empty author: "No stations yet" / "Create one with New station, from a template or straight from a prompt." :178; fetch error Alert (message + Retry); action error danger Alert; Table "load more" control from shared Table.

## Screen: Station detail (S/StationDetail.tsx; inline view in the Stations tab via `?station={id}`; also reused by capabilities/stations and CreateStationScreen)
Permission: read for all; every write control is `write`/`canAuthor`. Step bar (Save/Check facts/Review claims/Publish/New draft version) renders nothing for non-authors (:268). Fact-check/produce only when `supportsFactCheck(scope)` (platform scope) and status not archived; BriefEditor only when `supportsBrief(scope)` and author.
### Header
- Back button "Stations" :317 (unsaved changes -> LeaveConfirmModal).
- Name input aria-label "Station name" :325 (editable drafts) else h2 title; caption `{exam_code} · version {n}` :340ish; StatusBadge.
- Icon actions: "New draft version" / "New draft from this" (archived) busy "Creating…" :343-345 (not shown while a draft); "Archive" (published) busy "Archiving…" :355-357; "Delete draft" (draft) busy "Deleting…" :367-369.
- Notes: "Template structure is not available in the catalogue. Reload templates or edit from the template list." :382; "No layout is defined for exam {code}. Create a station template for this exam first." + link "Create a station template" :390 -> `/authoring/station-templates/new`.
### Step guide (parts/stationPipeline.ts; steps via StepGuide)
- Steps: "Draft" (note "Written" / "Nothing written yet"), "Check facts" (note "Not checked" / "{n} to resolve" / "Checked by hand" / "{n} claims checked[ by hand]"; platform scope only), "Publish" (note "Live" / "Archived" / "Not published") (stationPipeline.ts:~35, fact-check/facts.ts:124-143).
- Next-action lines: "The agent is working on this version." ; "Checking facts against the guidelines…" / "Checking facts, {d} of {t} claims…" ; "Archived. Past attempts keep it; start a new draft version to edit." ; "Published and live. Its details are below, read only. Start a new draft version to change it." ; "Unsaved changes. {blocker}" / "You have unsaved changes. Save them before the next step." ; "Say what the station tests below and the agent drafts it." ; "Fill in the station below, then save." ; "Read the draft, then check its facts against the guidelines." ; "{n} to resolve: each claim needs your decision, then save." ; "Ready. Publishing makes this version the one candidates are assessed against." (stationPipeline.ts:~82-135).
- Step-bar buttons :276-287: "Save" (disabled on blocker), "Check facts", "Review claims", "Publish", "New draft version". Save blockers: "Give the station a name." / first validation error / "Fill all required fields." :198-201; publish error "Please fill all required fields." :243.
- Errors: danger Alert for action; "The last {fact check|script check|agent run} failed: {message}" :456.
### Draft step content
- Panel "What should it cover?" (ProduceForm; platform scope, empty draft): label "What should it cover?", hint "A topic, your notes or a case pasted whole. With nothing written the agent drafts it, then checks the facts and corrects what the sources contradict." :300, button "Produce" / "Producing…" (fact-check/ProduceRun.tsx:41-55).
- RunLog panel "Agent run": description `{n} steps · {n} tokens`; badges "Stopping after this step" / "Working", button "Stop"; outcomes "Finished", "Stopped", "Ran out of time", "Reached its token budget", "Reached its step limit", "Stopped answering", "Ended"; headings "Changed or left for you", "Steps" (ProduceRun.tsx:11-123).
- Fold "Station content" (open when drafted or no fact-check) :483; caption "Version {n}." + " Edit the sections below; Save in the bar above stores them." / " Published, so it is read only. Create a new draft version to edit." :485-488; body = StationInstanceContentPanel (the template-driven block editors, see Template builder blocks below).
- BriefEditor (S/BriefEditor.tsx): Panel title "Reading brief" :40, description "What the candidate reads before the station starts. Saving this does not cut a new version." :41, button "Save brief" / "Saving…" :68.
- Fold "Produce again from a brief" (closed) :510.
### Facts step (platform scope; fact-check/FactCheck.tsx)
- Panel "Check the facts" :518. Intro: "Each claim is looked up in the guideline library and on the clinical web. Nothing changes unless you accept a correction." / "{n} claims, checked {when} against the guideline library and the clinical web. Nothing changes unless you accept a correction." / "{d} of {t} claims checked so far. You can act on them once all are in." :421-424; button "Check again" / "Checking facts…" :428-429.
- Tabs aria "Claims": "To resolve" (empty "No source contradicts it."), "Unconfirmed" ("Every claim was found in at least one source."), "Supported" ("No claim is supported yet."), "Resolved" ("No correction has been accepted or dismissed yet.") :34-47; success Alert "Every claim is supported by a source." :450; empty "Claims found. The first verdicts arrive in about half a minute." / "No claim here could be checked against a guideline." :474-475.
- Claim card: badge "Sources disagree"; decision badges "Corrected by the agent" / "Removed" / "Correction made" / "Kept as written"; source rows "Guideline library", "Clinical web", verdicts "Supports", "Contradicts", "Nothing found"; reliability "Reliable", "Standard", "Other"; "Nothing here settles this claim." / "This source was not asked."; "page {n}".
- Ruling controls: "On {where} now", field label "Change it to", "Suggested: {new}. This check is older than the…", buttons "Make this change", "Remove it", "Mark as fixed", "Keep as written", "Undo correction" / "Reopen", notes "The removed words stay out; add them back yourself if needed." / "The corrected words stay; edit them back yourself if needed." :219-290.
### Publish step
- Panel "Publish" :549; text "Publishing makes v{n} the version candidates are assessed against. A published version is what an attempt was marked against, so it is archived rather than deleted." :552; warning Alert "This station has no candidate brief, so candidates see nothing during reading time. You can still publish." :557; per-incomplete-step warning `{label}: {note}.`; button "Publish anyway" :578.
### Dialogs
- Archive/Delete ConfirmModal: title `Delete draft v{n} of "{title}"?` / `Archive v{n} of "{title}"?` :436; confirm "Delete" / "Archive" :439; body StationUsedBy + `stationConfirmCopy` (S/versions.ts:45-48): delete "The draft is removed. Published versions are untouched. If this is the station's only version, the station is deleted with it."; archive "Past attempts stay intact. If an older version is still published, the station stays in the live library on that one; otherwise it is retired from the live library."
- LeaveConfirmModal (foundation/ui/LeaveConfirmModal.tsx): title "Leave without saving?", message "You have unsaved changes. If you leave now they will be lost.", buttons "Leave" / "Stay".
### StationUsedBy (S/StationUsedBy.tsx): "Not used anywhere yet" / "Used {n} time(s): by circuits, attempts, peer sessions and practice sets" (:9-10); short label "Used by {n}" / "Not used" (:15); `v{n}: {label}.` ; retry button "Try again" :36.
### StationVersionHistory (S/StationVersionHistory.tsx): fold "Revision history" :41; empty "No revisions listed" / "This station has one version, and it is the one above." :50-51; rows `v{n}`, stamp "Archived {date}" / "Published {date}" / "Never published" :82-84, ` · {usedByLabel}`.
### Legacy meta: LegacyStationMeta (:597) shows legacy station id/name for imported stations.

## Screen: New station (stations/CreateStationScreen.tsx; route /app/[workspace]/authoring/stations/new, metadata title "New station")
Permission: `RequireAuthor` (author_content); non-authors see Alert "Only an organisation administrator can edit this." (parts/CannotAuthor.tsx:8). After save the screen swaps to StationDetail (the draft) and replaces the URL with `?station={id}`.
### Header (PlatformTemplateWizardPageLayout)
- Title "New station" :63; subtitle "Choose a published template and fill in content manually or with AI. Saving opens the draft to check its facts and publish." :64; back link "Stations" (to `/authoring/stations`).
### Tabs
- "Manual" :93; "Generate with AI" :95 (shown when platform scope or a template is chosen).
### Fields
- Fold "Station details" :120. "Station title" label :124, placeholder "e.g. Chest pain counselling" :131.
- "Template" select :135: first option "No template: write it from a prompt" :143; options `{template title} (v{n})` (published versions only, parts/useCreateStationChoices.ts:48); help "Only published templates can be used for stations. A station with no template is still a real station. It just borrows the exam's own shape rather than a reusable one."
- "Exam" select (when no template): "Select an exam…" :173, options exam names.
- "Station type" select (when no template and exam has subtypes): "Choose the kind of station…" :194; help "These stations are scored differently, so the prompt is steered by the type rather than left to guess."
- Fold "Generate draft" :212 (AI tab): description "Paste a short prompt (a few lines). We'll auto-fill the template fields below; you can edit anything afterward."; textarea placeholder "e.g. 72F falls at home, hip pain, shortened externally rotated leg. Candidate to assess and plan management including peri-op considerations." :219; button "Generate draft" / "Generating…" :234.
- Content: StationInstanceContentPanel (template-driven editors) when a structure exists; else "Generated draft" card: "Generated draft" / "Read this before you publish. It is not live until you save." (stations/GeneratedDraft.tsx); else empty card: title "This exam needs a template" / "Choose a template or an exam" :251; body "This exam has no built-in station layout. Create a station template for this exam here. It is published when you save it, and you come straight back to this station." + link "Create a station template" / "The full station form appears here as soon as you pick a published template, or say which exam this station is for."
### Footer
- "Cancel" :271, "Save draft" / "Saving…" :279 (disabled until title and exam/template, and no template needed).
### States and errors
- Alert info (no published templates): platform "No published templates yet. You can still write a station straight from a prompt by choosing its exam below." :79; org "No published templates yet. You can still write a station by choosing its exam below. Choose a published template to generate a draft with AI." :80; templates load error danger Alert; exam catalogue LoadError with Retry.
- Form errors (hooks/useCreateStationForm.ts): "Could not load template." :114; "This template has no exam assigned." :121; "Choose a template, or say which exam this is for." :147,198; "Drafting from a prompt alone is the platform catalogue's. Choose a published template to generate against, or write the station yourself below." :161; "Failed to generate content." :185; "Please enter a station title." :194; "Please fill all required fields." :213; "Failed to create station." :228.

## Dialog: Import from PDF or Word (imports/ImportStationDialog.tsx; opened from the Stations tab, author only)
Permission: button is `write` (author_content). Dialog uses AuthoringDialog.
- Title "Import from PDF or Word" :212; lead "Upload a station you have already written. We copy its words into a template. Nothing is added or rewritten." :213.
- Buttons: "Cancel"; commit "Upload" / "Upload {n} files" :216, busy "Uploading…" :217 (disabled until a file, an exam and loaded templates).
- Labels: "Exam" (AuthoringExamSelect, required) :226; "Template" select :239 with options "{Simulation scenario (ASPiH)} (standard)" :249 (offered when the org has no copy), published template titles, "Make a new template from this file" :256.
- Dropzone :270-276: "Drop the file here", "Drop your station files, or click to choose" / "Drop one station file, or click to choose", or the chosen filenames; help "PDF or Word (.docx), one station per file, up to 10MB each." :279 + " You can add several files at once." / " Your first file sets the template. After you publish it you can add the rest together." :281-282.
- Recent imports (section aria "Recent imports", heading "Recent imports" :290): per file row: filename, status line (importCopy.ts:20-31): "Reading the file and drafting a template. This takes about a minute." ; "Template drafted. Review it, then create the station." / "Template drafted. Review it; creating the station also publishes the template." ; "Copying the file into the template. This takes about a minute." ; "Draft station created. It is in your Stations list." ; "Could not be imported"; spinner label "Working" :357.
- Row actions: link "Review the template" :378 (new tab to the template editor); button "Create the station" / "Publish template and create the station" / "Starting…" :381-390.
- Check notes after completion: "Every part of the template was filled word for word from your file." ; "Left empty because your file had nothing for them: {ids}." ; "Check these against your file, the wording may differ: {ids}." (:440-455).
- Errors: "That file is larger than 10MB." / "Only PDF and Word (.docx) files can be imported." / "A new template is made from one file. Choose one." / "We could not take that file." (:406-410); upload failures "{file}: It is not a PDF or Word file we can read, or it has nothing in it." / "Too many imports just now. Wait a minute and upload the rest again." (importCopy.ts:8,11); imports list error Alert.

## Tab: Templates (S/StationTemplatesSection.tsx; route /authoring/station-templates)
Permission: read for all; header buttons and row actions are `write` (author_content). Platform-owned templates are read-only in an org scope except "Copy to my organisation" and "New draft" (`canManageTemplate`).
### Buttons
- "Import from PDF or Word" :112 (opens ImportStationDialog); "Create station template" :121 -> `/authoring/station-templates/new`.
- Lead :126: "Define layout and fields for clinical stations. Saved drafts and published versions appear below, but not the starting layouts on the new-template wizard."
- "Load more templates" / "Loading…" :235; error "Could not load more templates: {message}" :224.
### Filters
- Exam select aria "Filter by exam"; search placeholder "Search templates…" :135, aria-label "Search station templates" :136.
### Row (AuthoringListRow)
- Title = template title; row click opens the edit/view screen; PublishStatusLine with kind label `{exam_code}` or `{exam_code} · Platform template`.
- Icon actions (tooltips): "Copy to my organisation" (busy "Copying…") :365 (org scope, platform template); "New draft" (busy "Creating…") :376; "Edit draft" (link to the edit screen) :386; "Publish draft" (busy "Publishing…") :393; "Archive live" (busy "Archiving…") :405; "Delete draft" (busy "Deleting…") :417.
### Dialog (ConfirmModal :278-305)
- Archive live: title `Archive live v{n}?` :281; confirm "Archive live" :290; body "Stations already built on it keep that shape; nothing new may bind to it." :297.
- Delete draft: title `Delete "{title}"?` (template only) / "Delete draft?" (has a live version) :283-285; confirm "Delete draft" :292; body "Draft v{n} will be removed permanently. Live v{m} stays published." :301 / "This removes the template entirely." :305; danger tone.
### States
- Card header "Station templates N" :143; empty title "No saved templates yet" :148, description "The layouts on New template are starting points only. They are not added here until you finish the wizard (Save draft), then Publish from this list." :149; loading skeleton; list error Alert + "Dismiss"; action error danger Alert.

## Screen: New station template (templates/StationTemplateNewScreen.tsx; route /app/[workspace]/authoring/station-templates/new, metadata title "New station template"; optional `?exam={code}&then=station`)
Permission: `RequireAuthor` (author_content); non-authors see "Only an organisation administrator can edit this." Two-step wizard (steps from templates/wizardSteps.ts: "Start" note "Choose exam and layout" / "Exam, name, layout"; "Sections & fields" note "Then save a draft"; only Back to step 1 is selectable from step 2).
### Header (PlatformTemplateWizardPageLayout)
- Title "New template" :49; subtitle "Choose the exam, name the template, pick a starting layout, then save a draft. Only saved (and published) templates appear in the catalogue list." :50; back link "Station templates" :52.
### Step 1: Start (TemplateStartPanel + TemplateLayoutGallery)
- "Exam" label :162 (AuthoringExamSelect, required; empty option "Select an exam…" :169); "Template title" label (structure/b2b/.../TemplateLayoutGallery.tsx:185) placeholder "Untitled template" :192.
- Gallery heading "Starting layouts" :155 (radiogroup; each card aria-label `{title}. {description}. {n} sections.`; shows "{n} section(s)"). Layout options (lib/stations/stationTemplateStartOptions.ts:21-64, title / description; order depends on the org): "Blank" / "Start from scratch"; "SCA" / "Patient, record, plan"; "PLAB 2" / "Brief, patient, plan"; "CASC" / "Brief, patient, plan"; "Clinical interview" / "Scenario, work-up, Q&A"; "Prioritisation" / "Trauma list and ordering"; "Communication" / "Consent, news, conduct"; "Portfolio" / "Brief and CV interview".
- Starting-layout section titles (lib/stations/v1/*): Clinical interview "Basic Information", "Key Concerns", "Clinical Assessment", "Interview Questions", "References"; Communication "Basic Information", "Communication Themes", "Communication Frameworks", "Interview Questions", "Key Learning Points", "References"; Prioritisation "Basic Information", "Patient Lists", "Suggested List Order", "Interview Questions"; Portfolio "Basic Information", "Interview Questions", "Key Learning Points", "References". PLAB/CASC/SCA fields are blocks (labels, e.g. PLAB: "Examination findings", "Doctor Identity", "Patient Information", "Task Instructions", "Explanation", "Differential Diagnosis", "Clinical Assessment", "Clinical Examination Findings", "Further Investigations", "Pharmacological Management", "Non-Pharmacological Management", "Health Education", "Follow Up", "Safety Netting", "Social Concerns", "ICE", "Additional Notes", "Specialties"; CASC: "Doctor Task", "Description", "Diagnostic Criteria", "Differential Diagnosis", "Explanation", "Assessment", "Risk Factors", "Immediate Actions", "Pharmacological Treatment", "Psychological Treatment", "Social Interventions", "Safety Planning", "Follow Up", "Additional Notes"; SCA: "Patient Biodata", "Recent Notes", "Current Medications", "Past Medical History", "Recent Investigations", "Social History", "Explanation", "Assessment", ...).
### Step 2: Sections & fields
- The shared Template builder (see next screen section).
### Footer
- "Back" (step 2) :194; "Cancel" :201; "Continue" (step 1) :219; commit "Save draft" (or "Save and publish" when `then=station`) / "Saving…" (step 2) :58.
### Errors
- "Please choose an exam." :209,233; "Please enter a template title." :213; title schema first message (b2bTemplateTitleSchema); "Failed to create template." :241; server errors shown in a danger box. After save returns to Templates tab; with `then=station` it publishes, then goes back to the new-station form.

## Screen: Edit station template version (templates/StationTemplateEditScreen.tsx; route /app/[workspace]/authoring/station-templates/[templateId]/versions/[version], metadata title "Edit station template")
Permission: `RequireAuthor`; editing only a draft version of a template the user may manage; otherwise read-only (fieldset disabled).
- Title = template title or "Edit draft" :62; subtitle `Version {n} is {status}, so it is read only. Make a new draft from the list to change it.` / `Version {n}. Published versions cannot be edited. Make a new draft from the list first.` :65-66; back link "Station templates" :69.
- Loading skeleton; error Alert + "Try again" :79; missing: "Template not found. It may have been removed." :84.
- Title input aria-label "Template title" :97 (max 200); StructureBuilder (disabled when not editable).
- Footer: "Cancel" (editable) / "Back" :114; "Save draft" / "Saving…" :140 (disabled when read only).
- Errors: "Only a draft version can be edited." :121; "Enter a title." :126; "Failed to save draft." :134.

## Component: Template structure builder (structure/b2b/components/features/stations/templates/builder/*; used by New template step 2, Edit template, and the platform staff mirrors)
Props: `kind="station"` (sections coloured by audience) or `"feedback"` (plain marking form).
### Shell (TemplateBuilderShell.tsx)
- Template title input placeholder "Untitled template" :45, aria-label "Template title" :46; heading "Template structure" :50; toolbar: persona select "Who speaks in the AI role" (StructureBuilder.tsx:133) with options "the patient" / "the examiner (viva)" (:148-149), icon buttons "Undo" / "Redo" (:154,161).
### Draft writing panel (TemplateGenerationPanel.tsx; station kind)
- Heading "Draft writing with AI" :83; body "When someone clicks Generate draft on a station from this template, the AI uses the exam type below plus built-in guidance for each field. You only need to add extra notes here or on individual fields if you want something different." :85-87; label "Exam type" :94 (select of generation profiles, "custom" included); help "Changing exam type replaces sections and fields below with that exam's default layout. Your optional AI notes above are kept." :111; fold "Built-in instructions for this exam (read-only)" :117 (aria "Built-in exam instructions for Generate draft"; "Loading…"); label "Extra notes for the AI (optional)" :133 placeholder "Anything you want the AI to always keep in mind for this template" :140; label "Your own main instructions" :145 placeholder "Replaces the usual exam instructions when exam type is Custom" :152 (only when custom allowed).
### Section list (SectionFilmstrip.tsx)
- Left column aria "Sections"; heading "Sections" :147 with count; empty "No sections yet." :159; row title or "Untitled section" :109; "{n} field(s)" + " · drop here" :112-113; drag handle aria-label "Drag to reorder section", title "Drag to reorder" :90-91; audience legend (station); button "Add section" :198. Narrow screens: SectionChipStrip (tablist aria "Sections", chip "Untitled section", "Section").
### Section stage (SectionStage.tsx)
- Empty: heading "Start with a section" :95; text "A section is written for the patient, the candidate or the examiner. Add one, then add the fields it needs." (station) / "Sections group related fields. Add one, then add the fields it needs one at a time." :99-100; button "Add your first section" :103.
- Section header: audience label or `Section {n}` :144; "{n} field(s)" :148; inputs placeholder "Section title" / aria "Section title" :155-156, placeholder "Add a short description (optional)" / aria "Section description" :165-166; action "Section settings" :170.
- Field list aria "Fields" :183; empty "No fields yet. Add the first one below." :192; per-row insert control aria-label/title "Insert field here" (AddFieldMenu.tsx:315); bottom AddFieldMenu; navigation aria "Section navigation": "Previous" :255, "Next section" :275.
### Field row (CanvasBlock.tsx)
- Drag handle aria "Drag to reorder field" / title "Drag to reorder" :80-81; label or "Untitled field" :96; "Required" marker aria/title :102-103; caption (type label).
### Add field menu (AddFieldMenu.tsx)
- Trigger "Add field" :282; menu aria "Add a field" :168 with heading "Add a field"; search placeholder "Search field types…" / aria "Search field types" :179-180; empty `No field type matches "{query}".`; groups (blockTypeLabels.ts:18-22): "Text", "Rich content", "Choices", "Scoring"; footer link "Field type guide" :239 (opens info modal).
- Field types (lib/stations/blockTypeLabels.ts:34-125, label / description): "Short text" / "One line of text. Good for names, dates, or brief answers."; "Long text" / "A box for several lines of text. Good for histories, notes, or longer answers."; "List" / "Add as many bullet points as needed. Good for drug lists, ideas, or open items."; "Media" / "Images, audio, video or PDFs, each with an optional caption. Good for radiographs, scans, heart sounds and letters."; "Records" / "A card per record with the columns you set. Good for a ward list of patients, each with age, summary and notes."; "Questions and answers" / "Numbered questions, each with its model answer. Good for viva or interview questions."; "Grouped list" / "Items under headings, each with optional reasons. Good for a suggested order split by theatre list."; "Pick one" / "Choose one option from a list you set. Good for yes/no, gender, or a single choice."; "Pick several" / "Tick any options that apply. Good when more than one answer is allowed."; "Checklist" / "A fixed list of items to tick off. Good for observation lists or marking criteria."; "Scale" / "Rate something on a number scale (e.g. 1–5). Good for confidence or graded scores."; "R/A/G criterion" / "Red, Amber, or Green score with supporting phrase and explanation, for one SCA toolkit skill." Station kind offers the first 8; feedback kind the scoring types.
- StationBlockTypesInfoModal.tsx: title "Field types for stations & templates", intro "These are the building blocks for station and feedback templates. Pick the type that best matches what you want trainees or examiners…", close button.
### Inspector drawer (InspectorPanel.tsx; aria `{title} settings`; close "Close settings" :146,175)
- Field drawer title "Field", subtitle = type label :65 (BlockInspector.tsx): "Label" (placeholder "What the author fills in") :79-85; "Answer format" select :92 (type labels); station kind: "Used in the station as" with role select (labels) and role description :105-132; toggle "Required" / "Authors must fill this in" :136-137; "Options (one per line)" :145 (pick one/several); "Items (one per line)" :160 (checklist); "Columns (one per line)" :181 + help "Each record shows these, in this order. Renaming a column keeps the values already written under it." :193 (records); "Min" :200, "Max" :212 (scale); "Feedback scoring path" :227 placeholder "e.g. global_skills.structures_consultation" :233, help "Links this marking row to the score and comments saved in feedback." :236 (R/A/G); "Generate draft instructions" :243 with "Loading exam model instructions…" :245, placeholder "Tell the AI what to write in this field when someone clicks Generate draft" :259, notes "This field is not in the exam catalog (common for blank templates and new fields). Add your own instructions here. They are saved on the template." :264 / "Starts from the exam model. Edit here to change it for this template only." :269; buttons "Duplicate" :280, "Delete field" :284.
- Section drawer title "Section", subtitle audience or `Section {n}`: "Written for" :38 radiogroup of audiences (lib/stations/blockRoles.ts:38-62): "Patient" ("The script the simulated patient follows. The candidate does not see this."), "Candidate brief" ("Notes the candidate reads before starting the station."), "Examiner" ("Model answers and marking notes for the examiner after the station."), "Faculty" ("Setup, debrief and teaching notes for the people running the station. Never shown to the learner or used by the AI."); "Title" label; "Description" label, placeholder "Shown above this section (optional)" :92; button "Remove section" :97.
### Instance editors (when a station is filled in from the template; pages/*, used by StationInstanceContentPanel)
- List editor: "None" (read-only empty), input aria `{label}: add new item` placeholder "Add new item", button "Add", aria `Edit {label} item {n}` / `Remove {label} item {n}`.
- Records: card title "Record", "Add record", aria `Remove record {n}`.
- Questions and answers: title "New question" or the question, placeholders "Question" / "Model answer", "Add question", aria `Question {n}`, `Answer {n}`, `Remove question {n}`.
- Grouped list: title "Unnamed group" or the name, aria `Group {n} name`, `Remove group {name}`, "Add group", help `One item per line. Start a line with "- " to add a reason under the item above.`
- Media: placeholder "Caption (optional)" (aria `Caption {n}`), placeholder "https://… (image, audio, video or PDF)" (aria `Add a URL to {label}`), "Add", aria `Remove item {n}`, upload dropzone (PhotoUpload), error "Could not remove that item."
- R/A/G grade control: "Red" / "Amber" / "Green" (RagGradeControls.tsx:33).

## Screen: New marking scheme (rubrics/RubricStartScreen.tsx; route /app/[workspace]/authoring/rubrics/new, metadata title "New marking scheme")
Permission: `RequireAuthor` (author_content).
- Title "New marking scheme" :59; subtitle "Start blank or from a published marking scheme. You get a draft to edit; nothing is used until you publish it." :60; back link "Marking schemes" :62.
- "Title" label :67, placeholder "Copy of {title}" (when copying) / "e.g. Consultation skills" :73; help "Set here; a marking scheme keeps its title across versions." :76.
- Search placeholder "Search published marking schemes…" :80, aria-label "Search starting points".
- Radiogroup aria "Start from" :83: cards with kind badge "Blank" / "OSCE Guide" / "Yours" (:18-20), `v{n}`, title, rating kind label (see Rating kinds) + ` · {n} competencies`, domain list joined by " · ".
- Button "Start blank" / "Copy and edit" :95 (disabled until a starting point is picked); danger Alert for errors; list loading/error via AsyncBoundary. On success opens the builder at version 1 of the new scheme.

## Screen: Marking scheme builder (rubrics/RubricBuilderScreen.tsx + RubricBuilder.tsx; route /app/[workspace]/authoring/rubrics/[rubricId]/versions/[version], metadata title "Edit marking scheme"; the route also passes the dashboard preview)
Permission: capability gate; editable only for a draft version of an org-owned scheme by an author (`readOnly` otherwise); platform schemes show "OSCE Guide catalogue".
### Header
- Title: scheme title (click to rename: title attr "Rename this marking scheme" :104; input label "Marking scheme title" :128; saves on blur; inline error); read-only shows plain title.
- Subtitle `Marking scheme · version {n}` + " · OSCE Guide catalogue" :54; back link "Marking schemes" :55; StatusBadge.
- Buttons: "New draft version" :172 (owned, version not draft, no draft exists); "Open draft version {n}" :177; "Copy to my marking schemes" :194 (platform scheme, org scope).
- Warning Alert "This marking scheme has no version {n}." :73.
### Step guide (rubricSteps.ts)
- Steps: "Draft" (note "Saved" / "Unsaved changes"); "Preview" (note "Checked" / "Checking…" / "{n} problem(s)" / "Needs instructions" / "No problems"); "Publish" (note "Live" / "Archived" / "Not published").
- Next-action line: "This version is read-only. Start a new draft to change it." ; "Checking the latest edit…" ; "Fix {n} problem(s) to publish." ; "Add marking instructions on the Marking tab to publish." ; "You have unsaved changes. Save them to publish." ; "Looks right in the preview. Publish this version." (rubricSteps.ts:52-70).
- Bar buttons (author, draft): "Draft instructions" :134; "Save draft" :137; "Publish" :140. Alerts: action error (danger); info note "Every place already has instructions." / "Drafted instructions for {n} place(s). Read them before you save." :110; warning "The draft could not be checked: {message}" :148.
### Editor tabs (segmented, aria-label "Marking scheme editor" :152)
- "Structure {n}", "Rating {n}", "Results & dashboard {n}", "Marking" (counts are open problems per tab).
### Tab: Structure (SectionEditor.tsx, CompetencyEditor.tsx, FieldEditor.tsx)
- Empty "No parts yet. Add a rated domain to start." :29; add buttons per kind (labels from Section kinds: "Rated domain", "Written section", "Single field").
- Part card title = title or kind label; badges kind / "{n} problem(s)"; controls "Move part up", "Move part down", "Remove part".
- Fields: "Heading" (single field) :77; "Domain" / "Section" placeholder "e.g. Data gathering" :83; "Id" (mono; hint "Lower case and underscores; results are stored under it.") :84; "Instructions to the marker" (2 rows) :86; "Fields" list heading; toggles "Judged live" (hint "Can be judged while the consultation is still running.") :102, "May be left out" (hint "One of several alternatives; a result may leave it empty.") :103, "What this alternative is" (placeholder "e.g. Clinical station feedback (Station 2)") :105; lists "Each competency answers" :107, "Answered once for the domain" :109.
- Competency card: "Untitled competency" :34, badge "Needs fixing", "Competency" (placeholder "e.g. Explores the patient's concerns") :40, "Id" :41, "What the marker looks for" :43, per-grade descriptors aria `Descriptor for {grade}` placeholder `A {grade} looks like…` :76-85, add button "Add competency" :51, controls "Move/Remove competency".
- Field card: "Untitled field" :123, "Needs fixing", "Label" (placeholder "What the reader sees") :129, "Answer" select (Field types) :132, "Role" :136, "Id" (hint "Always the rating's field name.") :139, "Written by" (empty label "The marker") :140, "At least" (hint "Fewest entries the marker must give.") :142, "Required" :145, "Instructions to the marker" (placeholder "What to write here, and how.") :149, "Options, one per line" :171, nested headings "Each entry holds" / "The group holds"; add control "Add a field" :79 / select option "+ Add a field…" :90; controls "Move/Remove field".
### Tab: Rating (RatingPanel.tsx)
- Fold "Rated as" :38 (cards for Rating kinds); fold "Grades and field name" :64; "Field name" :68 with help "What each competency's grade is stored as, e.g. score. Renamed in every domain." :83; scale editor: aria `Grade {n}`, "Remove" (aria `Remove grade {g}`), "Add grade" :137 (new grades "Grade {n}"); range: "Lowest", "Highest", "Values" (options "Whole numbers" / "0, 1, 2 and so on, with no halves."; "Any number" / "Halves and decimals allowed.") :18-19,94-96.
### Tab: Results & dashboard (DisplayPanel.tsx)
- Fold "Each domain" (description "The figure each domain gets, and the line a domain must reach.") :41: "Domain result" (empty "Default") :43, "Domain pass line" (hint "Leave empty for no domain pass line.") :44.
- Fold "Station total" (description "The one figure for the whole station, and what passes.") :48: "Total" :51, "Out of" (hint "Empty: worked out from the marking scheme.") :52, "Pass line" :53, toggle "Every domain must pass too" (hint "A station passes only if each domain reaches its own pass line.") :57-58.
- Fold "Tones" (description "Colour a rating by how far up the scale it sits: atLeast is a fraction from 0 to 1.") :64: "From (0–1)", "Tone", "Add tone", controls "Move/Remove tone".
- Fold "Bands" (description "Name ranges of the total, e.g. 0–4 “Not yet”, 5–7 “Borderline”.") :69: "From", "To", "Name" (default "Band"), "Tone" (empty "None"), "Add band".
- Fold "Wording" (description "Replace the default headings on the feedback page and dashboard.") :73: five text fields from Display labels.
### Tab: Marking (MarkingPanel.tsx)
- Fold "Marking instructions" :50: label "Marking instructions (system prompt)" :52, help "What the marking model reads before the transcript. A version cannot be published without it." :65.
- Fold "Pacing, in seconds" :69: "Whole station" (hint "How long the station lasts."), "Introduction ends" ("Must come before history ends."), "History ends" ("When the patient moves on from history."), "Safety-net window" ("The last stretch, counted back from the end.") :10-13.
- Fold "Examiner layout" :92: "The form a human reviewer fills in for a slot." + " Platform catalogue marking schemes need one before they can be published." (platform scope) :95; body = the Template structure builder in `kind="feedback"` mode (scoring field types; see Template builder above).
### Right column
- ProblemList: "Checking…" / "No problems. This marking scheme can be published." :48; "{n} problem(s) to fix before publishing" :56 (each problem is a button that jumps to the field; messages come from the server preview endpoint).
- Panel "Preview" (description "What a candidate sees, from a made-up result.") :173; tabs aria "Preview": "Feedback page", "Dashboard" (when the dashboard slot exists); empty "Checking the draft…" / "Fix the problems to see the preview." :177.
- Panel "Trial mark" (description "Mark a real conversation against this version. Nothing is saved.") :180: source tabs aria "Trial source": "Paste a transcript", "An attempt" :51-52; "Transcript" label :62; attempt search placeholder "Search by candidate or station…" / aria "Search attempts to trial-mark" :137-138, radiogroup aria "Attempt", empty "No marked attempts found." :140, row `{station title or "Station removed"} · {date}` + "{n} turn(s)" :181-185; buttons "Trial mark" / "Marking…" :85, "Stop" :89; result line "Marked by {model or "the marker"}. Not saved anywhere." :100; blocked "A trial needs a marking scheme with no problems." :184; errors danger Alert, "The trial could not be marked." :96; badge `{word} · {s} s · {n} turn(s)`.
### Option vocabularies (rubricVocabulary.ts, label / hint)
- Rating kinds :41-44: "Red / Amber / Green" / "Three grades, G best and R worst."; "Named scale" / "Your own grades, best first (e.g. Excellent, Good, Fair, Poor)."; "Number range" / "A score between a minimum and a maximum, e.g. 0 to 10."; "Met / not met" / "Each competency is either met or not."
- Section kinds :48-50: "Rated domain" / "Competencies, each rated and answered the same way."; "Written section" / "Fields the marker writes once, with no rating."; "Single field" / "One answer on its own, e.g. an overall summary."
- Field types :54-60: "Rating", "Short text", "Long text", "List", "Pick one", "Group", "Records" (hints e.g. "The competency's grade, on the marking scheme's rating.", "A line: a name, a heading, a verdict.", "A paragraph: evidence, an explanation.", "Several short lines, e.g. actions to take.", "One of the options you list.", "A few fields answered together, once.", "A repeating group, e.g. one row per finding.").
- Field roles :64-73: "Rating", "Evidence", "Explanation", "Strength", "Improvement", "Action", "Flag", "Summary", "Selector", "Other" (hints "The grade itself.", "What the candidate said or did.", "Why the grade was given.", "Shown as something done well.", "Shown as something to work on.", "A next step for the candidate.", "A concern the reader must not miss.", "An overall comment.", "Picks which variant of the station applied.", "Shown plainly, with no special treatment.").
- Field sources :77-78: "The marker" / "The marking model writes it."; "The platform" / "Filled in after marking, never by the model."
- Domain aggregates :82-85: "Count each grade", "Sum", "Average", "Percent achieved"; total aggregates :89-92: "Share at the best grade", "Sum", "Average", "Percent achieved".
- Tones :96-100: "Excellent", "Good" (drawn green), "Fair" (amber), "Weak", "Poor" (red).
- Display labels :104-108: "Domain chart subtitle", "Domain pass line label", "Station total title", "Trend chart subtitle", "Pass line label".

## Routes: feedback templates (no UI)
- `app/app/[workspace]/authoring/feedback-templates/new/page.tsx` redirects to `../rubrics`; `feedback-templates/[templateId]/versions/[version]/page.tsx` redirects to `../../../rubrics`. Feedback templates became the "Examiner layout" inside a marking scheme version (Marking tab).

## Tab: Programmes (S/ProgrammesSection.tsx; route /authoring/programmes, org scope only)
- Covered in full in `3-people-programmes.md` (section "/programmes"). In the Build hub it is the 3rd tab "Programmes"; the nav also has a separate "Programmes" entry (author_content) on the assess surface (`surfaces/assess/surface.ts:49`).

## Hire vs institution labels (Build hub)
- No noun-driven string in the Build hub uses `useAssessWords`; the hire surface shows the same strings as the institution. Differences are only outside this hub (People/Candidates, sitting/assessment). Candidate, sitting and trainee words that do appear in authoring are fixed literals: "candidate" (station and brief copy), "sitting(s)" (exam retire/delete copy, marking scheme archive copy, exam next-action lines), "trainees" (field types info modal).
- Nav label for the hub is "Build" on both surfaces (`surfaces/assess/surface.ts:47`, `surfaces/hire/surface.ts:29`); the page title is "Authoring".

## Not found / out of scope
- Staff-console mirrors (`app/staff/authoring/**`) reuse the same components with platform scope (adds Approve/Withdraw approval, fact-check, produce, partner-pilot).
- Upload dropzone strings inside `PhotoUpload` (foundation) and the generic `ListCard`/`Table` pagination labels are shared components, not re-listed.

Screens: 17, controls: 981

<!-- parts/5-shell-hire-partner.md -->
# Part 5: shell, hire, partner (baseline, read-only inventory)

Paths relative to `web/src/` unless stated. Dated 2026-11-05. Strings in quotes with file:line.

## Permissions behind the menus
- Backend answers (`api/app/features/tenancy/service_workspace.py:104-114`): `read_org`; `manage_team` = org admin; `run_circuits` = org admin OR assigned staff (supervisor); `schedule_sittings` = org admin; `sign_off_results` = institution admin only; `export_results` = org admin; `author_content` = org admin (or platform admin when no org).
- Roles (`api/app/features/tenancy/domain.py:17-28`): ORG_ADMIN = owner, admin, institution_admin, partner_admin; INSTITUTION_ADMIN = owner, admin, institution_admin; supervisor = ASSIGNED_STAFF_ROLE; trainee / practice_user = end users.
- Web union `foundation/session/permissions.ts:9-20`. Nav is filtered by `can()` only, never by role string (`surfaces/assess/surface.ts:20-25`).
- Effective split: `run_circuits` is "staff vs everyone else" (`surfaces/assess/surface.ts:27-35`, `surfaces/hire/surface.ts:15-19`).
- Workspace kind from org_type: "partner"|"employer" else "institution" (`foundation/routing/workspace.ts:87-89`). Kind picks the arm: institution -> assess, employer -> hire, partner -> partner (`surfaces/assess/surface.ts:138`, `hire/surface.ts:36`, `partner/surface.ts:41`; `surfaces/registry.ts:45-51`, fallback assess).

## Workspace landing (`/app`, `/app/[workspace]`)
- `app/app/page.tsx:24-34`: not ready -> nothing; `can(session,"administer_platform")` -> "/staff"; else `workspaceBasePath(landingWorkspace(user, lastWorkspace(user.id)))`. Renders `Redirecting`.
- `landingWorkspace` (`surfaces/resolveWorkspace.ts:59-66`): remembered workspace slug if still available; else the FIRST non-personal workspace (membership order); else personal ("me"). Comment: a person with an institution "is there to work".
- `app/app/[workspace]/page.tsx:16-27`: always `router.replace("/app/<slug>/dashboard")` with `PageSpinner`. Role is NOT consulted: every role lands on `/dashboard`.
- Consequence: a trainee/candidate (nav has no "dashboard" item) lands on `/dashboard`; the assess/hire `dashboard` screen is declared for all (`ASSESS_SCREEN_NAMES`, `surfaces/assess/surface.ts:86-87`) so what a trainee sees there depends on the screen component (see parts on `domains/assess`; not inventoried here).
- `layout.tsx` (`app/app/[workspace]/layout.tsx:24-71`): RequireSession; spinner until ready; unknown/non-member slug -> `notFound()`; `rememberWorkspace(userId, slug)`; suspended org replaces the shell with `OrganisationSuspended` (name from workspace). 
- `screen.tsx:22-50`: arm not owning the screen name -> `notFound()`; screen loader pending -> `PageSpinner`; no component -> notFound.
- `capability.tsx:16-21` + `useCapabilityGate.ts:20-49`: capability pages (Settings, Stations, Authoring, Notifications...) 404 ("missing") unless the arm mounts them and the permission is granted; Stations has `unmountedGoesTo: "/mocks"` (bounce, `capabilities/stations/capability.ts:20`).

## Shell frame (WorkspaceShell)
`surfaces/WorkspaceShell.tsx`
- Skip link "Skip to content" (:124). Grid: 5rem rail on md, 15rem sidebar on lg, collapsible; help dock column only when Athena offered (:113-118, :169).
- Nav items = manifest.nav() then mounted capabilities (:61-79); ungrouped items first, then sections in `NAV_SECTIONS` order: customers, revenue, catalogue, operations, practice, connect, general (`capabilities/navSection.ts:14-22`; section labels via `NAV_LABELS`: "Catalogue", "Practice", "Connect", "General" ... :30-37).
- Sidebar `detail` under the workspace name = `manifest.label` for non-Train: assess "Institution", hire "Hiring", partner "Partner" (`WorkspaceShell.tsx:131`; labels `assess/surface.ts:137`, `hire/surface.ts:35`, `partner/surface.ts:40`).
- Nav landmark aria-label "<label> sections" e.g. "Institution sections" (`WorkspaceSidebar.tsx:53`).
- Toolbar root crumb = `workspace.name` for org workspaces (:147).
- Athena (help dock + toolbar "Help" button + "ask" rows): `athenaOffered = !isOrgSurface` -> NOT offered for assess, hire, partner (`capabilities/surface.ts:49-52`).
- Inbox unread count requested only if an item with key "inbox" is in nav (`WorkspaceShell.tsx:83-84`): never in assess/hire/partner (inbox capability is `surfaces: ["train"]`, `capabilities/inbox/capability.ts:13`).
- Train-only: ChooseExam gate, PeerPracticeProvider (:103, :162). Org shells wrap children in `PendingFeedbackProvider` (:161).

## Menu: org admin (institution, role owner/admin/institution_admin)
Has run_circuits, manage_team, author_content. Source `surfaces/assess/surface.ts:35-52`. Flat, ungrouped, in this order (permission in brackets; "-" = none beyond run_circuits):
1. "Overview" -> /dashboard (LuGauge) [-]  (:40)
2. "Sittings" -> /sittings (LuCalendarDays) [-]  (:41)
3. "Results" -> /results (LuClipboardCheck) [-]  (:42)
4. "Now running" -> /live (LuRadio) [-]  (:43)
5. "People" -> /trainees (LuUsers) [-]  (:44)
6. "Reporting" -> /reporting (LuChartNoAxesColumn) [-]  (:45)
7. "Team" -> /team (LuUserCog) [manage_team]  (:46)
8. "Build" -> /authoring (LuPencilRuler) [-]  (:47)
9. "Stations" -> /authoring/stations (LuBookCopy) [author_content]  (:48)
10. "Programmes" -> /programmes (LuListChecks) [author_content]  (:49)
Then mounted capabilities, section "General": "Settings" -> /settings (`capabilities/account/capability.ts:14-20`, permission null, all arms).
NOT shown to staff: capability "Stations" (library; `staffRefusedOn: ["assess","hire"]`, `stations/capability.ts:19`) and capability "Authoring" (`staffNavHiddenOn: ["assess","hire"]`, `authoring/capability.ts:30`; `registry.ts:80-82`). Debrief and Transcripts are `hidden:true`. No "Practice sessions", "My training", "Self practice" (comment :31-34 "Their own training is not in it").
Note: "Build" has no permission, so a supervisor sees it too; Build is a hub whose tabs are gated on their own (comment :36-38).

## Menu: supervisor (role "supervisor": run_circuits only)
Same list minus items gated: no "Team" (manage_team), no "Stations", no "Programmes" (author_content). Result: Overview, Sittings, Results, Now running, People, Reporting, Build; General: Settings.

## Menu: trainee (institution; no run_circuits) `assess/surface.ts:53-82`
Ungrouped: 
1. "My training" -> /trainee (LuGraduationCap)  (:61)
2. "Practice sessions" -> /mocks (LuLayers)  (:73)
Section "Practice" (`section: "practice"`):
3. "Self practice" -> /trainee/practice (LuSparkles)  (:75-81)
4. "Stations" -> /stations (capability, permission null, `stations/capability.ts:14-18`, path "/stations"; not hidden for non-staff)
Section "General": "Settings" -> /settings.
Order inside Practice: own items first, then mounted capabilities (Self practice, Stations) (`WorkspaceShell.tsx:78`).
Comment: "There is no 'is a trainee' permission and there should not be one" (:54-60).

## Menu: hire admin (employer org, admin role) `surfaces/hire/surface.ts:14-31`
Ungrouped, in order:
1. "Overview" /dashboard (:22)  2. "Assessments" /sittings (LuBriefcase) (:23)  3. "Results" /results (:24)  4. "Now running" /live (:25)  5. "Candidates" /trainees (:26)  6. "Team" /team [manage_team] (:28)  7. "Build" /authoring (LuPencilRuler) (:29).
No "Reporting", no "Stations"/"Programmes" nav entries (hire has fewer than assess), no Practice sessions. General: "Settings". Hire supervisor: same without "Team".
Hire reuses Assess screens (`screensFrom: "assess"`, :39), so /reporting, /programmes, /authoring/stations URLs still resolve (manifest.screenNames = ASSESS_SCREEN_NAMES includes reporting, programmes; :38) though not in the menu.

## Menu: hire candidate (employer, no run_circuits)
1. "My assessments" -> /trainee (LuGraduationCap) (`hire/surface.ts:18`) -- only own item.
Section "Practice": "Stations" -> /stations (capability mounted on hire too, `stations/capability.ts:15`; hide only for staff). No "Practice sessions", no "Self practice". Section "General": "Settings".
Doubt flagged: mocks screens are in ASSESS_SCREEN_NAMES so hire URLs /mocks resolve though absent from hire menu.

## Menu: partner admin (partner org) `surfaces/partner/surface.ts:27-36`
1. "Overview" -> /dashboard (LuGauge) (:29)
2. "Reporting" -> /reporting (LuChartNoAxesColumn) (:30)
3. "Team" -> /team (LuUserCog) [manage_team] (:33)
Capabilities: section "Catalogue": "Authoring" -> /authoring [run_circuits or administer_platform] (`authoring/capability.ts:26-32`; `staffNavHiddenOn` does NOT include "partner", so it shows); section "General": "Settings".
Partner screenNames: dashboard, reporting, team only (`partner/surface.ts:43`). Gating by nav is not applied to Overview/Reporting: any partner member (any role) sees both; partner Team = Assess `Team` screen with `orgSlug` (`partner/screens.tsx:30-31`).
Note: Authoring page for partner exists as capability route; org-type partner admin has run_circuits via `is_org_admin` (partner_admin in ORG_ADMIN_ROLES).

## Sections and labels summary
| Arm | Ungrouped | Practice | Catalogue | General |
|---|---|---|---|---|
| assess staff | 7-10 items | (hidden) | (hidden) | Settings |
| assess trainee | My training, Practice sessions | Self practice, Stations | - | Settings |
| hire staff | 5-7 items | (hidden) | (hidden) | Settings |
| hire candidate | My assessments | Stations | - | Settings |
| partner | Overview, Reporting, [Team] | - | Authoring | Settings |
Items that exist for Train only and are NOT in these shells: "Notifications" (/notifications, connect), "Contact & Feedback" (/messages, connect; `help/messagesCapability.ts:10-18`), "Achievements", Help (hidden, train+platform), community, peer practice, study media. Their route files exist (`app/app/[workspace]/notifications|messages|help|inbox`) but `Capability` gate returns 404 on org arms. `/inbox` redirects to `/notifications` (`inbox/page.tsx`).

## Toolbar (WorkspaceToolbar, md and up; none on phones)
`surfaces/WorkspaceToolbar.tsx`
- Breadcrumb nav aria-label "Breadcrumb": `<section> > <page>` via `resolveCrumb` (:64-70). Root label = workspace name. Section/page labels from nav items and `NAV_LABELS` (`capabilities/navSection.ts:30-49`): sittings -> "Sittings", circuits -> "Circuit", slots -> "Review", trainee -> "My training", mocks -> "Practice sessions", stations -> "Station", attempts -> "Attempt". These are institution words even in a hire workspace (not vocabulary-aware).
- Search pill (lg): "Search" + "⌘K" (:78-79); icon-only button aria-label "Search" below lg (:84).
- `NotificationsBell`: renders null on assess/hire/partner (inbox capability is train-only; `capabilities/inbox/NotificationsBell.tsx:14`). Label when shown "Notifications" / "Notifications, N unread".
- "Help" outlined button + `openAthena()`: only if `athena` -> never on org arms (:90-99).
- Shortcut: Ctrl or Cmd + "k" toggles the palette (:47-52), anywhere in the shell.

## Jump-to palette (Ctrl/Cmd+K)
`surfaces/WorkspaceJumpTo.tsx`, `jumpTo.ts`, `jumpToSearch.ts`
- Modal title "Search" (:129); input placeholder and aria-label "Search stations, help, pages" (:154-155) (said even though org shells search neither stations nor help; see below). Results listbox aria-label "Results" (:159).
- Rows, in order: group "Pages" = every shell nav item whose label contains the typed text (case-insensitive; all when empty) (:90-96, `jumpTo.ts:2-5`). Then "Stations" (library search), "Help" (articles), and the ask-Athena row (group from `helpPersona`).
- Org arms: `scope.stations = consumer` = false (:44 of toolbar) so no Stations group; `athena=false` drops Help articles and the ask row (:104, :112). Remote search still calls `fetchHelpArticles` (`jumpToSearch.ts:43`) but the rows are discarded. So on assess/hire/partner the palette = nav labels only: admin 10 entries (assess) / 7 (hire) / 3-4 (partner incl. Authoring, Settings); includes the "General"-section items "Settings", and for trainees "Stations".
- Exactly the same label set as the sidebar (it takes `items`, `WorkspaceShell.tsx:146`); no hidden pages (Debrief/Transcripts hidden:true are excluded by capabilitiesFor).
- Keys: ArrowDown/ArrowUp move (stops at ends, `jumpTo.ts:8-11`), Enter runs active row, Esc closes via Modal; hover sets active.
- States: "Nothing matches “{query}”." (:184); "Searching…" (:186, after >= 2 chars, 250ms debounce, `jumpToSearch.ts:7-9`); alert "Some results could not load. Try again." (:189).

## Workspace switcher
`surfaces/WorkspaceSwitcher.tsx`; shown in sidebar under logo (`WorkspaceSidebar.tsx:143`), hidden at md (rail) and when collapsed; on phones inside the drawer.
- Lists `workspacesFor(user)` = personal "me" first then each membership (`resolveWorkspace.ts:49-52`). Personal workspace name from `PERSONAL_WORKSPACE`.
- One workspace -> no menu, name + detail only, hidden on phones (:69-71). Detail line for org arms: "Institution" | "Hiring" | "Partner".
- Button: aria-haspopup "menu", aria-expanded; chevrons icon; Spinner while switching (:80-88). Menu role="menu"; items role="menuitem": org icon (LuBuilding2) or person icon (LuUser) + name; check mark on current (:104-122). Click outside closes.
- Choosing: close; same slug = no-op; else `selectWorkspace(orgSlug)` (re-mints token) then `router.push("/app/<slug>")` (:45-47) -> hits the `/dashboard` redirect.
- No labels such as "Switch workspace" exist; no org-type badge in the list; a hire org and an institution look identical in the list.

## Sidebar chrome
`surfaces/WorkspaceSidebar.tsx`, `NavRailList.tsx`
- Phone top bar: button aria-label "Open menu"/"Close menu" with an accent dot if unread>0 (never for org arms); "Reload" button only in installed-PWA standalone (:62-86). Backdrop button "Close menu" (:177-183).
- lg: "Collapse sidebar" / "Expand sidebar" buttons (:108-126); md: icon rail with right-side tooltips of the label (`NavRailList.tsx:25-37`).
- Section headings only for non-empty sections: "Practice", "General", "Catalogue" (`b2cNavSectionLabel`, :126). Active item `aria-current="page"` via `isNavActive`.
- `onSignOut` prop of NavRailList is NOT passed by WorkspaceSidebar, so no in-list "Sign out" (sign-out lives in the footer).

## Footer (WorkspaceNavFooter)
`surfaces/WorkspaceNavFooter.tsx` (org arms: `consumer=false`, `staff=false`)
- No "Upgrade to Pro" (consumer only, :46-58).
- Org arms: if `isPlatformAdmin(session)` a link "Staff console" -> /staff (:110-116); otherwise nothing above the user row.
- User row: initials avatar (aria-hidden), name (`session.user.name` else email else "Account"), email line only when a name exists (:42-43, 119-135); sign-out icon button aria-label/title "Sign out", Spinner label "Signing out", disabled + aria-busy while pending (:60-79).
- Collapsed rail: only the sign-out button (:81-88).
- "Your exams did not load. Try again" alert is `consumer`-only (:41).

## Home / notifications / help / messages in org shells
- No "Home" item in any org menu. Landing is `/dashboard` (above). Train's "Home" is not present.
- Notifications (`/notifications`): capability `inbox`, surfaces ["train"] -> no nav item, no bell, no unread; URL 404s on org arms (Capability gate). `/inbox` redirects to `/notifications` then 404s.
- Help (`/help`, dock, toolbar button, Athena): ["train","platform"] only; none in assess/hire/partner (`athenaOffered`, `capabilities/surface.ts:52`). No help entry exists for an institution/hire/partner user.
- Messages "Contact & Feedback" (`/messages`): ["train"] only -> 404 on org arms. An org user has no in-app way to message OSCE Guide staff.
- Settings (`/settings`): the only account entry, "General" section, on every arm (`account/capability.ts:16`).
- Org shells do mount `PendingFeedbackProvider` (`WorkspaceShell.tsx:161`) and ship the OrganisationSuspended full-screen replacement.

## Hire vs institution vocabulary
`domains/assess/vocabulary.ts`, hook `useAssessWords.ts` (`assessWordsFor(surface)`: "hire" -> employer, else institution, `vocabulary.ts:47-49`). Only `hire` is switched; partner (no Assess screens besides Team) uses institution words.
| Key | Institution (`vocabulary.ts:18-30`) | Hire (`:32-44`) |
|---|---|---|
| sitting | "sitting" | "assessment" |
| sittings | "sittings" | "assessments" |
| Sitting | "Sitting" | "Assessment" |
| Sittings | "Sittings" | "Assessments" |
| trainee | "trainee" | "candidate" |
| trainees | "trainees" | "candidates" |
| Trainee | "Trainee" | "Candidate" |
| Trainees | "Trainees" | "Candidates" |
| People | "People" | "Candidates" |
| scheduleSitting | "Schedule a sitting" | "Schedule an assessment" |
| addPeople | "Add people" | "Add candidates" |
Nav-level words are separate hard-coded strings, not from the vocabulary:
| Nav | Assess `surface.ts` | Hire `surface.ts` |
|---|---|---|
| dashboard | "Overview" | "Overview" |
| sittings | "Sittings" | "Assessments" |
| results | "Results" | "Results" |
| live | "Now running" | "Now running" |
| trainees | "People" | "Candidates" |
| reporting | "Reporting" | (absent) |
| team | "Team" | "Team" |
| build | "Build" | "Build" |
| stations / programmes | "Stations" / "Programmes" | (absent) |
| trainee home | "My training" | "My assessments" |
| mocks | "Practice sessions" | (absent) |
| self practice | "Self practice" | (absent) |
Where `useAssessWords` is applied (17 hits, 16 files): Sittings.tsx, SittingDetail.tsx, NewSitting.tsx, PeopleTabs.tsx, roster/{Roster,TraineesPanel,AddTraineePanel,BulkImportDialog,AccessPanel}.tsx, trainee/{TraineeHome,MySittingDetail}.tsx, dashboard/OrgDashboard.tsx, results/ResultsIndex.tsx.
Where institution words are still hard-coded and leak into hire (grep of quoted literals in files that do NOT use the hook): SittingActions.tsx ("Cancel this sitting?", "Cancel sitting", "A circuit on this sitting has started..."), SittingEditForm.tsx ("Edit this sitting", "Save sitting", "This sitting has begun..."), SittingFields.tsx ("Feedback straight to the trainee", "You cannot add trainees once it has started"), SittingFilterBar.tsx (aria-label "Filter sittings"), TraineePicker.tsx (title "Trainees", "Find a trainee"), results/Results.tsx (back label "Sitting"), roster/TraineeEditDialog.tsx ("Edit trainee"), roster/GroupsPanel.tsx ("Trainee groups"), roster/CohortsPanel.tsx ("Each trainee can be in one cohort"), reporting/Reporting.tsx ("all of its sittings"), plus `NAV_LABELS` (sittings -> "Sittings", trainee -> "My training", mocks -> "Practice sessions": breadcrumb). Mixed output is therefore possible in one hire screen (for example "Assessments" title with "Cancel this sitting?").
Wording in `ResultsIndex.tsx:112` special-cases `w.sitting === "sitting" ? "a sitting" : "an assessment"` (an inline article hack).
Surface labels: assess "Institution", hire "Hiring", partner "Partner"; assistant packs: assess "admin", hire "employer", partner "admin" (`capabilities/surface.ts:28-38`).

## Partner arm: screens and registry
`surfaces/partner/surface.ts`, `screens.tsx`
- Screens owned: "dashboard", "reporting", "team" only (`surface.ts:43`). Any other route 404s (no /sittings, /results, etc.), but `/authoring` and `/settings` resolve through capabilities.
- Partner slug = `workspace.orgSlug ?? ""` is passed as the growth `{partner}` path segment (`screens.tsx:20`). A partner org slug must equal the partner name (e.g. "bmj"); otherwise the growth routes 4xx/empty.
- Landing: `/app/<slug>/dashboard` -> PartnerDashboard.
- `surfaces/partner/surface.test.ts` exists (26 lines): not read.

## Partner Overview (PartnerDashboard)
`domains/partner/Dashboard.tsx` + `capabilities/attribution-dashboard/*`
- Page header title `${partnerDisplayName(partner)} dashboard`, "bmj" -> "BMJ On Exam dashboard"; other slugs -> slug with -/_ as spaces, UPPERCASE + " dashboard" (`viewModel.ts:344-348`, `Dashboard.tsx:83`). Missing slug -> "our partner dashboard".
- Subtitle: "See how people from your links are using OSCE Guide. All dates are UK calendar days." (:84)
- Segmented tabs aria-label "Partner dashboard sections" (:90); partner tabs in order (`tabs.ts:27-31`): "Overview", "Performance", "Your fee", "How we count" (id definitions). Tab in URL `?tab=` (invalid -> overview, `tabs.ts:36-39`). Never "Revenue".
- Filter bar (`DashboardFilterBar.tsx`) on all four tabs (scope "full"): one bordered group with selects "Date range" (options "This month", "Last month", "Last 30 days", "Last 3 months", "Last 6 months", and "Custom" or the active custom range label; `presets.ts:22-29`) and "Exam" (options "All exams", "SCA", "PLAB", "ORTHO"; `types.ts:9`); no Partner select in partner mode (:149). Summary line `<exam or All exams> · <utm campaign> · <d Mon yyyy – d Mon yyyy> · UK calendar days` (`presets.ts:105-115`, :171). "Reset filters" button when any filter differs from default (this month, no exam/campaign) (:172-180). Filters live in URL: from_date, to_date, partner, exam, utm_campaign (`useAttributionFilters.ts:52-70`); no UI for utm_campaign. Default range = this month.
- Custom date range modal (title "Custom date range"; lead "Choose the start and end dates for this report."; section "Date range"; date inputs "From", "To" with min 2026-01-01 and max today; buttons "Cancel", "Apply"). Errors (`presets.ts:80-85`): "Choose both a start and an end date."; "The start date must be on or before the end date."; "The end date can't be in the future."; "There's no data before 2026-01-01; the pilot started this year."
- "Updated HH:MM" (en-GB, local clock) shown once summary has loaded (`UpdatedAt.tsx`).
### Tab Overview
- Summary fetch `GET growth/partners/{p}/reporting/summary`, funnel fetch via staff-growth `readPartnerFunnel` (`api.ts`, `Dashboard.tsx:49-56`).
- Banner (role=note) "Estimated fee (guide only)" + `fee.billing_disclaimer` + "We're using £X per link visit." or, when no fee: "Fee estimates are a guide only" / "The fee shown here is an estimate from our arrival counts. You invoice from your own click records; nothing on this page is a bill." (`Banners.tsx:50-69`).
- Hero card: eyebrow "Overview", title "How your links are performing", hint "Visits, sign-ups, and your estimated fee for this period." (`copy.ts:111-113`). Empty (no visits, sign-ups, paid, fee): "No activity yet" / "When people open your links, the numbers will show up here." Else 3 MetricCards (`viewModel.ts:173-205`): "Link visits" (+ " N unique person/people." in tooltip), "Sign-ups", "Estimated fee" (£). Tooltips (info button aria-label `What "<label>" means`; open on click, Esc/outside closes): Link visits "How many times someone opened a page with your link."; Sign-ups "New accounts where we recorded you as the source they came from."; Estimated fee "A rough guide: your link visits in this period times our agreed rate per visit. You invoice from your own records."
- Defined in copy but NOT shown to partner: "Unique people", "Paid", "Sign-up rate", "Paid rate", "Repeat visits", "Revenue"(tooltip "Not shown on the partner dashboard."), spend items.
- Funnel card: title "From visit to payment", subtitle "How many people reached each step"; steps "Visited", "Signed up", "Paid" numbered 1-3, each with "% of visits" and count ("-" if unknown) (`Charts.tsx:46-100`, `viewModel.ts:52`). Empty: "Nothing to show for these dates" / "Try widening the date range or removing filters."
- Failure states (`LoadFailure`: danger Alert, `<error.message> <note>`, button "Try again"): summary "We couldn't load these numbers" note "Nothing here is zero; it just hasn't loaded."; funnel "We couldn't load the funnel" (empty note). Loading and empty come from `AsyncBoundary`.
### Tab Performance
- Cards: "Link visits over time" (bar; subtitle "How many times people opened your links"; empty "No link visits in this date range" / "Try widening the date range or removing filters."; series "Link visits"); "Sign-ups over time" (area; subtitle "New accounts from your links"; empty "No sign-ups in this date range"; series "Sign-ups"); "By exam" (hidden when an exam filter is set; subtitle "How link visits split across SCA, PLAB, and Ortho."; donut centre = total, label "link visits"; rows exam, "N% of visits", "N visits", "N sign-ups"; empty "Nothing to show for these dates"). Bucket day/week/month from range (`bucketForRange`). Flat or empty series shows the empty state.
- Failures: "We couldn't load performance", "We couldn't load sign-ups over time", "We couldn't load the breakdown by exam" (note "Other sections are unaffected.").
### Tab Your fee
- Fee banner again (above) and "Estimated fee over time" (bar; subtitles "Daily|Weekly|Monthly estimated fee from your link visits"; default "Estimated fee from your link visits"; empty "No link visits in this date range" / "Your estimated fee appears when people open your links."; bar tooltip "£X (N visits)"; axis "£<n>"). Failures: "We couldn't load the fee note", "We couldn't load the fee estimate".
### Tab How we count (Methodology)
- Card eyebrow "Plain English"; title "How we count your results"; body "These are the rules behind the numbers you see here. If something looks wrong, tell us the dates you were viewing and what seemed off." Headings "What the numbers mean" and "How we decide who gets credit". Definitions shown to partner (internalOnly dropped): "Link visit", "Unique people", "Sign-up", "Paid", "Estimated fee" (mentions "pilot default £0.40"). Rules: "Which link gets credit", "How long we remember a visit" (90 days), "Date range", "Filters" (`copy.ts:109-282`, `Methodology.tsx:94-141`).
- Caveat: the "Paid" definition and "Unique people" appear in the glossary though the cards do not show them.

## Partner Reporting (PartnerReporting)
`domains/partner/Reporting.tsx`
- Header "Reporting" / "Your tracking references, and who can see the numbers." (:30-33)
- Panel "Tracking references": list of `ref_id` with `<EXAM> · <landing_path>` line, no actions; empty state "No references yet" / "A reference appears here the first time somebody arrives through one of your links." Loading/error via `AsyncBoundary` default.
- Reporters: if `can(session,"administer_platform")` (OSCE Guide staff viewing a partner) -> `ReportersPanel`: table title `<NAME> viewers`, description `People at <NAME> who can sign in to see this dashboard.`; empty "No viewers yet" / `Add someone from <NAME> to share this dashboard.`; columns "Viewer", "Added" (yyyy-mm-dd), row button "Remove" -> confirm title `Remove access for <email>?`, message "They will no longer be able to sign in to this dashboard.", confirm "Remove access"; button "Add viewer" -> modal `Add <NAME> viewer` (text "No email is sent: tell them to sign in with this address (they can create an account with it if they have none). They can only see this dashboard, not the exam product."; input "Work email", placeholder "name@bmj.com"; warning "This isn't a <NAME> address. Double-check it: whoever signs in with this address will be able to see this partner's commercial data."; empty error "Please enter an email address."; buttons "Cancel", "Add viewer"/"Adding…"); toast "Viewer added"; load failure "We couldn't load viewers" + "Try again" (`staff-growth/bmj/ReportersPanel.tsx`).
- Else (every partner team member): Panel "Who can read this": "A reporter sees these numbers and nothing else. Ask OSCE Guide staff to add someone. Reporters are added by us, not by your team." (:38-42). So a partner admin cannot add a viewer.

## Partner Team (Assess `Team` reused)
`surfaces/partner/screens.tsx:30-31` renders `domains/assess/team/Team.tsx` with `orgSlug`. Header "Team"; tab strip aria-label "Team sections" with tabs "Members", "Add people", "History" (`Team.tsx:15-18,41,52`). Same screen for assess/hire Team. Words not vocabulary-aware. (Detail of members/invite/history belongs to the roster/tenancy inventory part.)

## Partner Authoring and Settings
Authoring (capability) is the only content-authoring entry for a partner, under "Catalogue" in the sidebar (`authoring/capability.ts`); Settings under "General". Not inventoried here.

## Gaps and oddities noticed (facts, no judgement)
- `/app/[workspace]` always redirects to `/dashboard`, with no role branching; a trainee lands on a route their menu does not list.
- Palette placeholder says "Search stations, help, pages" in org shells that offer neither stations nor help.
- NAV_LABELS breadcrumb section names are not vocabulary-aware ("Sittings", "My training").
- Hire has no "Reporting", "Stations", "Programmes" menu entries though the routes resolve.
- Org shells have no Home, Notifications, Help or Contact entries and no bell.
- Partner "Overview" and "Reporting" show for every partner member regardless of role; only Team is gated.
- Partner has a hard-coded "BMJ On Exam" name and `PILOT_PARTNERS = ["bmj"]`, `PILOT_EXAMS = ["sca","plab","ortho"]`, `EARLIEST_DATE = "2026-01-01"` (`types.ts:7-9`, `presets.ts:9`).

Screens: 12, controls: 78
