# Circuit console

Source: `boards/Console.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Formal exam | 2. Training | 3. Before start and ended | 4. Badges and alerts | 5. Listen in | 6. Mark a finished station | 7. Circuit feedback | 8. What was changed by hand | 9. Late arrivals refusals

## Always on screen (menu, header, notes, build spec)

SM

St Mary's Medical School

Administrator

[Home](Today.dc.html)

Run

[Sittings](Sittings.dc.html)
[Now running](LiveBoard.dc.html)
[Results](Results.dc.html)

Organise

[People](People.dc.html)
[Exams](Exams.dc.html)

Insight

[Reporting](Reporting.dc.html)

[Settings](Settings.dc.html)

[‹ March mock](Sitting.dc.html)

Circuit console

# Circuit 1 · Amara Okoye

Station 2 of 6 · Consultation · Supervisor: Dr Patel

[?] [Edit](EditCircuit.dc.html) (Live

The patient has not joined this station. Resend the patient if this does not clear.

[{{ t.label }}]
What changed: the four steps (Reading, Consultation, Marking, Done) are named on screen and every control says what it does before you press it.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/circuits/[circuitId]`

Who sees it
Any staff member; transcripts and review only for the circuit's supervisor

Owner agent
`institution-owner` · prove with `verify-institution` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/sessions/CircuitRunner.tsx`

- `web/src/domains/assess/sessions/SupervisorControls.tsx`

- `web/src/domains/assess/sessions/RunnerStepper.tsx`

- `web/src/domains/assess/sessions/StationProgressList.tsx`

- `web/src/domains/assess/sessions/ObserverPanel.tsx`

- `web/src/domains/assess/sessions/LiveMarkingSidebar.tsx`

- `web/src/domains/assess/sessions/InterventionsLog.tsx`

- `web/src/domains/assess/sessions/TurnStrip.tsx`

- `web/src/domains/assess/sessions/AddTraineesDialog.tsx`

- `web/src/domains/assess/sessions/OverrideDialog.tsx`

- `web/src/domains/assess/sessions/RunnerHelpPanel.tsx`

- `web/src/domains/assess/sessions/useCircuitRun.ts`

API calls (all exist; add no endpoint, change no schema)

`GET /api/v1/orgs/{org_slug}/circuits/{circuit_id}/console`Read Circuit Console
No screen calls this today.

`GET /api/v1/orgs/{org_slug}/circuits/{circuit_id}/console/stream`Stream Circuit Console
No screen calls this today.

`GET /api/v1/orgs/{org_slug}/circuits/{circuit_id}/interventions`List Interventions
No screen calls this today.

`GET /api/v1/orgs/{org_slug}/station-versions/{version_id}/sections`Read Staff Sections
Now: web/src/domains/assess/sessions/api.ts

`PATCH /api/v1/orgs/{org_slug}/circuits/{circuit_id}/auto-advance`Set Auto Advance
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/circuits/{circuit_id}/advance`Advance
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/circuits/{circuit_id}/end`End Circuit
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/circuits/{circuit_id}/extend-clock`Extend Clock
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/circuits/{circuit_id}/jump-to`Jump To
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/circuits/{circuit_id}/observer-token`Observer Token
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/circuits/{circuit_id}/pause`Pause
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/circuits/{circuit_id}/redo-station`Redo Station
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/circuits/{circuit_id}/resend-patient`Resend Patient
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/circuits/{circuit_id}/reset-clock`Reset Clock
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/circuits/{circuit_id}/resume`Resume
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/circuits/{circuit_id}/start`Start Circuit
No screen calls this today.

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.

## Tab 1: Formal exam

Start the circuitRunning

On stationAmara Okoye · station 2 of 6

Reading timeDone for this station

ConsultationPatient is live · Breaking bad news

06:42

ConsultationServer clock

## Controls

[Next station] [Pause] [Extend the clock] [Reset the clock] [Resend the patient] [End circuit]

[x] Moves to the next station automatically when time is up. When off, the circuit waits for you before each new station.

Not started yet? One button: Start circuit. Every override asks for a reason, kept with the record.

## Station progress

CandidateStationPhaseLeft

AO
Amara Okoye1 · Chest pain history(Completed[Review](SlotReview.dc.html)

AO
Amara Okoye2 · Breaking bad news(In consultation06:42[Mark](SlotReview.dc.html)

AO
Amara Okoye3 · Abdominal examination(Not started

## Station content: Breaking bad news

▸ Candidate brief

You are the FY1 on a medical ward. Mrs Jones's CT shows a mass…

▸ Patient script

Opening line, history, ideas, concerns and expectations.

▸ Examiner notes

What a good answer covers; red flags.

▸ Faculty material

Teaching points.

## The room
(Listening

Listening in is subscribe-only: you can hear the consultation and cannot be heard in it.

The patientIn the room · Speaking

Amara OkoyeIn the room
[Stop listening]

## Mark a finished station

Chest pain history

The full marking form for this station opens here, the same as Slot review.
[Mark Chest pain history](SlotReview.dc.html)

## Share this circuit's feedback

Marked on 1 of 6 stations. Not published yet. You can publish once at least one station is marked; this is the step that finalises the circuit's feedback.
[Go to circuit feedback](CircuitReview.dc.html)

▸ What was changed by hand

09:31 Clock extended · "Fire alarm test" · Dr Patel09:12 Patient resent · No reason was given.

## Tab 2: Training

## Stations on this circuit
[Add trainee]

Tap a name to jump the circuit to that station

[1 · Farah Ali · Chest pain] 2 · Gil Moss · Bad news · Patient is live[3 · Hana Lee · Abdomen]

[Redo this station (Farah Ali)]

Start the circuitRunning

On stationAmara Okoye · station 2 of 6

Reading timeDone for this station

ConsultationPatient is live · Breaking bad news

06:42

ConsultationServer clock

## Controls

[Next station] [Pause] [Extend the clock] [Reset the clock] [Resend the patient] [End circuit]

[x] Moves to the next station automatically when time is up. When off, the circuit waits for you before each new station.

Not started yet? One button: Start circuit. Every override asks for a reason, kept with the record.

## Station progress

CandidateStationPhaseLeft

AO
Amara Okoye1 · Chest pain history(Completed[Review](SlotReview.dc.html)

AO
Amara Okoye2 · Breaking bad news(In consultation06:42[Mark](SlotReview.dc.html)

AO
Amara Okoye3 · Abdominal examination(Not started

## Station content: Breaking bad news

▸ Candidate brief

You are the FY1 on a medical ward. Mrs Jones's CT shows a mass…

▸ Patient script

Opening line, history, ideas, concerns and expectations.

▸ Examiner notes

What a good answer covers; red flags.

▸ Faculty material

Teaching points.

## The room
(Joined

The patient
Audio only

You
Camera on

Farah Ali
No camera

[Mute microphone] [Turn camera off] [Stop listening]

## Mark a finished station

Chest pain history

The full marking form for this station opens here, the same as Slot review.
[Mark Chest pain history](SlotReview.dc.html)

## Share this circuit's feedback

Marked on 1 of 6 stations. Not published yet. You can publish once at least one station is marked; this is the step that finalises the circuit's feedback.
[Go to circuit feedback](CircuitReview.dc.html)

▸ What was changed by hand

09:31 Clock extended · "Fire alarm test" · Dr Patel09:12 Patient resent · No reason was given.

## Tab 3: Before start and ended

## Circuit 2 · Not started

Everyone is in. Starting begins reading time for station 1.
[Start circuit]

## This circuit has ended.

Its stations can still be marked and its record read.
[Mark a finished station](CircuitReview.dc.html)

## Tab 4: Badges and alerts

(● Live (Reconnecting… (Paused (Ended

The patient has not joined Station 2.

Station 3's attempt failed. Resend the patient or redo the station.

Voice fault in the room. The candidate may not hear the patient.

The clock is overdue by 40 s.

## Tab 5: Listen in

## Listen in

You can hear the consultation without being heard in it. Nothing you do here reaches the candidate or the patient.
[Listen in]
Amara Okoye
Speaking

Patient
Not in the room yet

## Training: camera and microphone

Amara
Audio only

Ben
No camera

[Mute microphone] [Turn camera off] [Stop listening]

## Tab 6: Mark a finished station

## Mark a finished station

[Station 1] [Station 2 (Unmarked]

The station's marking form opens here, the same as Mark this station.
[Open Mark this station](SlotReview.dc.html)

## Tab 7: Circuit feedback

## Share this circuit's feedback

Shares one summary of all the marking on this circuit. Candidates see it as their feedback. If you edit it and share again, the new version replaces the old one.

‹textarea: Anything to say about the circuit as a whole (optional)›

Not published yet.

You can share feedback once at least one station has been marked.
[Publish circuit feedback]
After: "Published 12 Mar 2026, 11:20. Publishing again replaces it." and the button reads "Publish again".

## Tab 8: What was changed by hand

## What was changed by hand

Advanced to the next station
09:41 · Dr Patel · Patient would not leave.

Paused
09:52 · Dr Patel · No reason was given.

Resumed
09:55 · Dr Patel

Clock extended
10:02 · Dr Patel · +60 s · Fire alarm.

Clock reset

Patient resent

Station redone

Jumped to a station

Auto-advance changed

Empty: "Nobody has stepped in on this circuit." Error: "Could not load the log."

## Tab 9: Late arrivals refusals

## Add trainee: refusals

Already on this circuit.

That station is not on this circuit.

An examination cannot take a late arrival: it is one candidate through every station.

## Dialog: help

## Observing an examination

One candidate, every station, on the examination's own clock. You are here to watch it and to mark it.

- Station progress updates as the candidate finishes each one.

- Listening in is subscribe-only.

- Mark a station from its row as soon as it has been sat.

[Dismiss help]

## Dialog: pause

## Pause the circuit

The clock stops for everybody. The patient stays in the room.

Reason (kept with the record)
‹input: The fire alarm went off›
Optional. Your answer is saved with the circuit.

[Cancel] [Pause]

## Dialog: extend

## Extend the clock

Adds time to the phase that is running now, for this station only.

Seconds to add
‹input: 60›

Reason (kept with the record)
‹input: The fire alarm went off›
Optional. Your answer is saved with the circuit.

[Cancel] [Add the time]

## Dialog: reset

## Reset the clock

Restarts the phase that is running now from its full duration.

Reason (kept with the record)
‹input: The fire alarm went off›
Optional. Your answer is saved with the circuit.

[Cancel] [Reset it]

## Dialog: resend

## Resend the patient

Dispatches a new patient to the station that is running. The consultation starts over for this candidate.

Reason (kept with the record)
‹input: The fire alarm went off›
Optional. Your answer is saved with the circuit.

[Cancel] [Resend]

## Dialog: end

## End the circuit

Stations nobody has sat are recorded as skipped. This cannot be undone.

Reason (kept with the record)
‹input: The fire alarm went off›
Optional. Your answer is saved with the circuit.

[Cancel] [End the circuit](CircuitReview.dc.html)

## Dialog: jump

## Jump to Hana Lee

The circuit moves to Abdominal examination. Stations passed over are recorded as skipped.

Reason (kept with the record)
‹input: The fire alarm went off›
Optional. Your answer is saved with the circuit.

[Cancel] [Jump to it]

## Dialog: redo

## Redo Chest pain history

Farah Ali sits this station again with a new patient. The first attempt stays on the record.

Reason (kept with the record)
‹input: The fire alarm went off›
Optional. Your answer is saved with the circuit.

[Cancel] [Redo it]

## Dialog: add

## Add somebody to this circuit

They are given a station at the end of the circuit, in the room that is already open.

[ ] Ivan Novak · ivan@stmarys.ac.uk

[ ] Jo Reid · Not yet joined: they can be added once they have signed in.

Station

‹select:
The station this circuit is running |

Chest pain history |
›

They take their turn after everyone already on the circuit.

[Cancel] [Add them]
