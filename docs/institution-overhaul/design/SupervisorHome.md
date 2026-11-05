# Home, supervisor

Source: `boards/SupervisorHome.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

## Always on screen (menu, header, notes, build spec)

SM

St Mary's Medical School

Supervisor

[Home](SupervisorHome.dc.html)

Run

[Sittings](Sittings.dc.html)
[Now running](LiveBoard.dc.html)
[Results 7](Results.dc.html)

Organise

[People](People.dc.html)

Insight

[Reporting](Reporting.dc.html)

Supervisor

# 7 stations to review

You review the circuits you lead. Your ratings are what count; the AI mark is a starting point.

Your next circuit

Year 3 practice round · Circuit B

Thursday 12 November, 09:00 · Training · 8 trainees, 8 stations

[Open the console](Sitting.dc.html)

The console opens when the sitting starts. Any staff member can run any circuit on the day; reviewing stays with the circuit's supervisor.

## Stations to review
Grouped by circuit

[

Final-year OSCE, March mock · Circuit A

5 of 8 candidates still to review

(5 to review›](Results.dc.html)
[

Year 4 mock · Circuit C

2 drafts waiting to be completed

(2 drafts›](Results.dc.html)
[

Year 3 practice, October · Circuit B

Every review done. Publish circuit feedback to finalise and let trainees read it.

(Ready to publish›](Results.dc.html)

## Circuits you lead
[All sittings](Sittings.dc.html)

Year 3 practice round · Circuit B

12 Nov · Training

(Scheduled

Final-year OSCE, summer finals · 6 circuits

26 Nov · Formal exam

(Scheduled

▸ Build spec: how to build this screen

Route
`/app/[workspace]/dashboard (supervisor)`

Who sees it
Supervisor

Owner agent
`institution-owner` · prove with `verify-institution` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/dashboard/SupervisorCircuits.tsx`

API calls (all exist; add no endpoint, change no schema)

`GET /api/v1/orgs/{org_slug}/supervisor/circuits`Read Supervisor Circuits
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
