# Sitting

Source: `boards/Sitting.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Circuits | 2. Candidates | 3. Results so far | 4. Primary action by step | 5. Other actions

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

[‹ Sittings](Sittings.dc.html)

Formal exam

# March mock

Today 09:00 · Final-year OSCE · Year group: Year 5

(Scheduled[Edit] [Cancel sitting] [Results](SittingResults.dc.html) [Open the console](Console.dc.html)

ScheduleDate set

Circuits8 candidates assigned

RunNot started

MarkNot started

DecideNot started

ReleaseNot started

Start the circuit from its console when everyone is ready.

[{{ t.label }}]
What changed: one primary button that follows the step (no second "Add a circuit"), and Edit gains the year group.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/sittings/[sittingId]`

Who sees it
Org admin and supervisors

Owner agent
`institution-owner` · prove with `verify-institution` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/SittingDetail.tsx`

- `web/src/domains/assess/SittingActions.tsx`

- `web/src/domains/assess/SittingEditForm.tsx`

- `web/src/domains/assess/sittingSteps.ts`

API calls (all exist; add no endpoint, change no schema)

`DELETE /api/v1/orgs/{org_slug}/circuits/{circuit_id}`Delete Circuit
Now: web/src/domains/assess/CircuitBuilder.tsx, web/src/domains/assess/EditCircuit.tsx, web/src/domains/assess/SittingDetail.tsx

`GET /api/v1/orgs/{org_slug}/circuits/{circuit_id}/edit-lock`Read Edit Lock
No screen calls this today.

`GET /api/v1/orgs/{org_slug}/sittings`List Sittings
Now: web/src/domains/assess/NewCircuit.tsx, web/src/domains/assess/NewSitting.tsx, web/src/domains/assess/SittingDetail.tsx

`GET /api/v1/orgs/{org_slug}/sittings/{sitting_id}`Read Sitting
Now: web/src/domains/assess/NewCircuit.tsx, web/src/domains/assess/NewSitting.tsx, web/src/domains/assess/SittingDetail.tsx

`POST /api/v1/orgs/{org_slug}/sittings/{sitting_id}/cancel`Cancel Sitting
Now: web/src/domains/assess/api.ts

`POST /api/v1/orgs/{org_slug}/sittings/{sitting_id}/circuits`Add Circuit
Now: web/src/domains/assess/SittingDetail.tsx, web/src/domains/assess/api.ts, web/src/foundation/routing/legacyRedirects.ts

`POST /api/v1/orgs/{org_slug}/sittings/{sitting_id}/circuits/bulk`Add Exam Circuits
Now: web/src/domains/assess/api.ts

`PUT /api/v1/orgs/{org_slug}/circuits/{circuit_id}`Rebuild Circuit
Now: web/src/domains/assess/CircuitBuilder.tsx, web/src/domains/assess/EditCircuit.tsx, web/src/domains/assess/SittingDetail.tsx

`PUT /api/v1/orgs/{org_slug}/sittings/{sitting_id}`Update Sitting
Now: web/src/domains/assess/NewCircuit.tsx, web/src/domains/assess/NewSitting.tsx, web/src/domains/assess/SittingDetail.tsx

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.

## Tab 1: Circuits

## Circuits
[Add a circuit](EditCircuit.dc.html)

[
Circuit 1 · Amara Okoye

Not started · 6 stations · Supervisor Dr Patel
](Console.dc.html) (Ready[Edit](EditCircuit.dc.html) [Delete]

[
Circuit 2 · Ben Hart

Not started · 6 stations · Supervisor Dr Patel
](Console.dc.html) (Ready[Edit](EditCircuit.dc.html) [Delete]

[
Circuit 3 · Chloe Imran

Not started · 6 stations · Supervisor Ms Clarke
](Console.dc.html) (Your circuit[Edit](EditCircuit.dc.html) [Delete]

5 more circuits · supervisors see their own circuit first

## Tab 2: Candidates

## Candidates

AO

Amara Okoye

Year 5 · signed in

Circuit 1

BH

Ben Hart

Year 5 · signed in

Circuit 2

CI

Chloe Imran

Year 5 · invited, not accepted · Resend invitation

Circuit 3

## Tab 3: Results so far

Stations marked0 of 48

Decided0 of 8

Released0 of 8

[Open results](SittingResults.dc.html)

## Tab 4: Primary action by step

## No date

Set a date so candidates know when to come.
[Set a date]

## No circuits

No circuits yet. Add at least one circuit so candidates can take this sitting.
[Add a circuit]

## Ready

Every circuit has a supervisor and candidates.
[Open the console]

## Finished

All circuits have ended.
[Open results]

## Tab 5: Other actions

Edit
Name, date and year group. Mode, exam and type lock once a circuit starts.

[Edit]

Cancel sitting
Only before any circuit starts.

[Cancel sitting]

Delete circuit
Only a circuit that never started.

[Delete]

Circuit 2 (Your circuit
Ms Clarke · 3 candidates

[Open the console](Console.dc.html)

Results

[Results](SittingResults.dc.html)

## Dialog: edit

## Edit sitting

Name
‹input: March mock›

Date
‹input: ›

Year group

‹select:
Final year |
›

[Cancel] [Save]

## Dialog: cancel

## Cancel this sitting?

Nobody can take it once it is cancelled. Nothing has started, so no attempt is lost.

[Cancel] [Cancel sitting]

## Dialog: del

## Delete Circuit 3?

Its candidates and stations come off this sitting. Nothing has been sat on it yet.

[Cancel] [Delete circuit]

## Dialog: delc

## Delete this circuit?

It never started, so nothing is lost.

[Cancel] [Delete circuit]
