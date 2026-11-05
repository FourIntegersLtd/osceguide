# Home, Today

Source: `boards/Today.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

## Always on screen (menu, header, notes, build spec)

SM

St Mary's Medical School

Administrator

[Home](Main.dc.html)

Run

[Sittings](Sittings.dc.html)
[Now running (1 live](LiveBoard.dc.html)
[Results 5](Results.dc.html)

Organise

[People](People.dc.html)
[Exams](Exams.dc.html)

Insight

[Reporting](Reporting.dc.html)

[Settings](Settings.dc.html)

Thursday 5 November

# Good afternoon, Dr Okafor

One circuit is running and five things need you.

[Schedule a sitting](ScheduleSitting.dc.html)

## Running now
[Open the live board](Today.dc.html)

(Live

Final-year OSCE, March mock · Circuit A

Station 4 of 8 · Supervisor: Dr Patel · 8 candidates

06:12 left

[Open console](Sitting.dc.html)

## Needs your attention
Oldest first

[(3 decisions

Record outcomes for Final-year OSCE, February

Every review is complete. Write the outcome and reason, then sign off.

›](Results.dc.html)
[(2 ready

Release results for Year 4 mock

Signed off. Candidates see nothing until you release.

›](Results.dc.html)
[(4 not joined

Trainees who have not accepted their invitation

They cannot be scheduled until they set a password. Resend in one step.

›](People.dc.html)

## Coming up
[All sittings](Sittings.dc.html)

[

NOV

12

Year 3 practice round

Training · 2 circuits · 16 trainees

(Scheduled](Sitting.dc.html)
[

NOV

26

Final-year OSCE, summer finals

Formal exam · 24 circuits · 24 candidates

(Scheduled](Sitting.dc.html)

Exams ready to schedule

3

Published stations

42

Trainees

186

Staff

9

▸ Build spec: how to build this screen

Route
`/app/[workspace]/dashboard (after setup)`

Who sees it
Org admin

Owner agent
`institution-owner` · prove with `verify-institution` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/dashboard/OrgDashboard.tsx`

- `web/src/domains/assess/dashboard/LiveNow.tsx`

API calls (all exist; add no endpoint, change no schema)

`GET /api/v1/orgs/{org_slug}/dashboard`Read Org Dashboard
Now: web/src/app/app/[workspace]/authoring/rubrics/[rubricId]/versions/[version]/page.tsx, web/src/app/app/[workspace]/page.tsx, web/src/app/app/[workspace]/screen.tsx

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
