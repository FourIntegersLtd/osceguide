# Results

Source: `boards/Results.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Needs a decision | 2. Ready to release | 3. All | 4. Empty and long lists

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

Run

# Results

Each sitting with how far its decisions have got.

## Needs your attention

[March mock: 5 candidates need a decisionDecide](SittingResults.dc.html)
[Year 4 mock: 3 results signed off and not yet releasedRelease](SittingResults.dc.html)
[2 stations waiting for your marksMark](SlotReview.dc.html)

[{{ t.label }}]

SittingDateKindCandidatesNot decidedDraftSigned offReleased
[March mockTodayFormal exam85120](SittingResults.dc.html) [Year 4 mock28 OctFormal exam120039](SittingResults.dc.html) [Year 3 practice round21 OctTraining16----](SittingResults.dc.html)
What changed: "Needs your attention" leads, built from the same counts plus the supervisor's unmarked stations.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/results`

Who sees it
sign_off_results

Owner agent
`marking-owner` · prove with `verify-marking` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/results/ResultsIndex.tsx`

API calls (all exist; add no endpoint, change no schema)

`GET /api/v1/orgs/{org_slug}/results`Read Results Index
Now: web/src/domains/assess/CandidateStepper.tsx, web/src/domains/assess/SittingDetail.tsx, web/src/domains/assess/SlotReview.tsx

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.

## Tab 4: Empty and long lists

## No results yet.

Results appear here once a sitting has trainees.

## Nothing here.

No sitting matches this tab.

Showing the 50 most recent sittings.
