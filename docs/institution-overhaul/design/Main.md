# Home, setup assistant

Source: `boards/Main.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

## Always on screen (menu, header, notes, build spec)

SM

St Mary's Medical School

Administrator

[Home](Main.dc.html)

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

Welcome

# Let's get St Mary's ready for its first sitting

Five steps. We show one at a time, and you can come back to any of them.

[?]

Step {{ stepNumber }} of 5

[
{{ s.mark }}
{{ s.label }}
Optional
]

({{ cur.tag }}

## {{ cur.title }}

{{ cur.body }}

{{ cur.whyTitle }}

{{ cur.why }}

[{{ cur.cta }}]({{ cur.href }})
[{{ cur.alt }}]({{ cur.altHref }})
[Skip for now]

How the pieces fit

Exam

What is examined and how it is marked

›

Stations

The cases candidates sit

›

People

Trainees and supervisors

›

Sitting

One occasion, such as the March mock

Exams ready

0

Published stations

0

Trainees

0

Staff

1

▸ Build spec: how to build this screen

Route
`/app/[workspace]/dashboard (until setup is done)`

Who sees it
Org admin; each step only to whoever can do it

Owner agent
`institution-owner` · prove with `verify-institution` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/dashboard/OrgDashboard.tsx`

- `web/src/domains/assess/dashboard/support.ts`

API calls (all exist; add no endpoint, change no schema)

`GET /api/v1/orgs/{org_slug}/dashboard`Read Org Dashboard
Now: web/src/app/app/[workspace]/authoring/rubrics/[rubricId]/versions/[version]/page.tsx, web/src/app/app/[workspace]/page.tsx, web/src/app/app/[workspace]/screen.tsx

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.
