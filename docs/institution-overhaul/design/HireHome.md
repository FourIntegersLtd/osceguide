# Hire overview

Source: `boards/HireHome.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

## Always on screen (menu, header, notes, build spec)

SM

St Mary's Medical School

Administrator

[Overview](HireHome.dc.html)

Run

[Assessments](Sittings.dc.html)
[Now running](LiveBoard.dc.html)
[Results](Results.dc.html)

Organise

[Candidates](People.dc.html)
[Exams](Exams.dc.html)

Insight

[Reporting](Reporting.dc.html)

[Settings](Settings.dc.html)

Acme Health Trust

# Overview

Your assessments, candidates and results.

[Schedule an assessment](ScheduleSitting.dc.html)

Running now

## Band 6 nurse assessment day

3 candidates on stations · Assessor: Dr Patel

[Watch it](LiveBoard.dc.html)

## Needs your attention
[4 candidates need a hiring decisionDecide](SittingResults.dc.html)

Candidates36

Assessors4

Assessments5

Same screens as the institution arm (screensFrom assess) with hire words: Candidate, Assessment, Assessor, Candidates page. Same blue, no teal. Nav now has Reporting and Exams (Programmes reachable), which hire lacks today. Decisions keep the recruitment outcome (Hired, Reserve list…), never shown to the candidate. Candidate nav: "My assessments".

▸ Build spec: how to build this screen

Route
`/app/[workspace]/dashboard (hire skin)`

Who sees it
Hire org admin

Owner agent
`institution-owner` · prove with `verify-institution` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/surfaces/hire/surface.ts`

- `web/src/domains/assess/vocabulary.ts`

- `web/src/domains/assess/useAssessWords.ts`

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
