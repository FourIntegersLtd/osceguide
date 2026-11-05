# Circuit feedback

Source: `boards/CircuitReview.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

## Always on screen (menu, header, notes, build spec)

SM

St Mary's Medical School

Supervisor

[Home](SupervisorHome.dc.html)

Run

[Sittings](Sittings.dc.html)
[Now running](LiveBoard.dc.html)
[Results](Results.dc.html)

Organise

[People](People.dc.html)

Insight

[Reporting](Reporting.dc.html)

[‹ Circuit 1 · Amara Okoye](Console.dc.html)

Marking and review

# Circuit 1 · Amara Okoye

Ended · 6 of 6 stations sat · Supervisor: Dr Patel

(Ended

Mark each station4 of 6 marked

Share the circuit's feedbackNot published yet

ResultsAdmin decides and releases

Mark the two stations left, then share one summary with the candidate.

## Stations to mark

[5 · Paediatric asthma(UnmarkedMark](SlotReview.dc.html)
[6 · Prescribing review(UnmarkedMark](SlotReview.dc.html)
[1 · Chest pain history(MarkedReview](SlotReview.dc.html)

3 more marked stations

## Share this circuit's feedback

Shares one summary of all the marking on this circuit. Candidates see it as their feedback. If you edit it and share again, the new version replaces the old one.

Marked on 4 of 6 stations

‹textarea: Anything to say about the circuit as a whole (optional)›

Not published yet.

[Publish circuit feedback](SittingResults.dc.html)

After publishing: "Published 5 Nov. Publishing again replaces it." and the button reads Publish again.

## What was changed by hand

09:31 Clock extended · "Fire alarm test"09:12 Patient resent · No reason was given.10:02 Auto-advance changed

## The record

Transcripts and automatic marking for each station open from its row. Only the supervisor named on this circuit can read what was said.

Today this is the lower half of the console once a circuit ends. It is drawn as its own step so a supervisor sees what is left. Same APIs: console, review, review/finalize, interventions.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/circuits/[circuitId] (after it ends)`

Who sees it
The circuit's supervisor

Owner agent
`marking-owner` · prove with `verify-marking` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/sessions/CircuitFeedbackCard.tsx`

- `web/src/domains/assess/sessions/LiveMarkingSidebar.tsx`

API calls (all exist; add no endpoint, change no schema)

`GET /api/v1/orgs/{org_slug}/circuits/{circuit_id}/review`Read Circuit Review
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/circuits/{circuit_id}/review/finalize`Finalize Circuit Review
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
