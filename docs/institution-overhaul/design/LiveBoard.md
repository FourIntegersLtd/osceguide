# Now running

Source: `boards/LiveBoard.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Now running | 2. Connection and warnings | 3. Earlier | 4. Nothing running

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

[{{ t.label }}]
What changed: it is in the Run section of the menu as "Now running".

▸ Build spec: how to build this screen

Route
`/app/[workspace]/live`

Who sees it
Org admin and supervisors

Owner agent
`institution-owner` · prove with `verify-institution` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/dashboard/LiveBoard.tsx`

- `web/src/domains/assess/dashboard/LiveNow.tsx`

API calls (all exist; add no endpoint, change no schema)

`GET /api/v1/orgs/{org_slug}/live`Read Live Board
Now: web/src/domains/assess/dashboard/LiveNow.tsx, web/src/domains/assess/dashboard/api.ts, web/src/domains/assess/dashboard/support.ts

`GET /api/v1/orgs/{org_slug}/live/history`List Live History
Now: web/src/domains/assess/dashboard/api.ts, web/src/domains/assess/dashboard/support.ts

`GET /api/v1/orgs/{org_slug}/live/stream`Stream Live Board
Now: web/src/domains/assess/dashboard/api.ts

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.

## Tab 1: Now running

Run

# Now running

Every circuit that is live in your organisation, updated as it happens.

(Live

The background worker is not running. This screen still moves due circuits on, but marking and clearing patients from rooms wait until it is back. Tell your platform admin.

Live

## 2 circuits running

March mock

[Open Circuit 4 · Dev Shah](Console.dc.html)

Circuit 4 · Dev Shah: a consultation is running but is not being recorded. Open the circuit and send the patient in again.

Circuit 4 · Dev Shah: The clock has run past this phase and the circuit has not moved on by itself. Advance it by hand.

## Running
Trouble first, then least time left
[

Circuit 1 · Amara Okoye

March mock · Formal exam · Station 2 of 6 · Breaking bad news · Amara Okoye · Dr Patel · room open

Reading › Consultation › Between(Consultation06:42](Console.dc.html) [

Circuit 4 · Dev Shah

March mock · Formal exam · Between stations · 3 of 6 sat · Dev Shah · Ms Clarke

Reading › Consultation › Between(Paused04:10](Console.dc.html)

Earlier · Today

[

Circuit 2 · Ben Hart

March mock · Formal exam · 1 candidate · 6 of 6 stations

09:00–10:24](CircuitReview.dc.html)
[

Circuit 5 · Esme Lowe

March mock · Formal exam · 1 candidate · 4 of 6 stations · ended early

09:00–09:58](CircuitReview.dc.html)

Earlier · Yesterday

[

Morning circuit

Year 3 practice round · Training · 6 candidates · 6 of 6 stations

14:00–15:10](CircuitReview.dc.html)

[Show earlier]

## Tab 2: Connection and warnings

(● Live (Reconnecting…

Live updates stopped. Reload to reconnect.

The voice service is not answering. New stations may not start.

Recording missing for Station 2.

Patient has not joined Circuit 1.

## Tab 3: Earlier

## Earlier

Yesterday

Feb mock · Circuit 1
Ended 11:40

Feb mock · Circuit 2
Ended 12:05

[Show earlier]

## Tab 4: Nothing running

## Nothing is running.

Circuits appear here the moment a supervisor starts one.
