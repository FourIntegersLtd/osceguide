# Reporting

Source: `boards/Reporting.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

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

Insight

# Reporting

Each exam across all of its sittings. The pass rate counts decisions released to candidates.

Exams

[Final-year OSCE
4 sittings · 52 candidates · 81% (34 of 42 released)
›](ExamDetail.dc.html)
[Year 4 mock
2 sittings · 24 candidates · Nothing released yet
›](ExamDetail.dc.html)
[Year 3 practice
6 sittings · 96 candidates · Nothing released yet
›](ExamDetail.dc.html)

## Per-sitting reports

Each sitting's report, CSV and readout live on its Results page.
[Open results](Results.dc.html)

Same data as today (GET reporting, one row per programme). Rows now open the exam. Empty: "No exams yet. Set up an exam and hold a sitting to see figures here." Hire gains this page (today it has no nav item).

▸ Build spec: how to build this screen

Route
`/app/[workspace]/reporting`

Who sees it
view_reporting

Owner agent
`institution-owner` · prove with `verify-institution` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/reporting/Reporting.tsx`

- `web/src/domains/assess/reporting/api.ts`

API calls (all exist; add no endpoint, change no schema)

No calls of its own: it is a static explainer or reuses the data of the screen that links here.

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.
