# Your result

Source: `boards/TraineeResult.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Released | 2. Not released yet | 3. Acknowledge

## Always on screen (menu, header, notes, build spec)

SM

St Mary's Medical School

Amara Okoye · Trainee

[My training](Trainee.dc.html)
[Practice sessions](Trainee.dc.html)
[Self practice](SelfPractice.dc.html)

Released 6 Nov

# Assessment outcome

[Download PDF]

[{{ t.label }}]
What changed: none.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/trainee/results/[sittingId]`

Who sees it
Trainee

Owner agent
`marking-owner` · prove with `verify-marking` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/trainee/MyResult.tsx`

- `web/src/domains/assess/trainee/ResultView.tsx`

API calls (all exist; add no endpoint, change no schema)

`GET /api/v1/me/results/{sitting_id}`Read My Result
Now: web/src/domains/assess/trainee/api.ts

`GET /api/v1/me/results/{sitting_id}.pdf`Read My Result Pdf
Now: web/src/domains/assess/trainee/api.ts

`POST /api/v1/me/results/{sitting_id}/acknowledge`Acknowledge My Result
Now: web/src/domains/assess/trainee/api.ts

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.

## Tab 1: Released

Outcome

## Pass, 72.4 / 100

Safe, well-structured consultations. Work on summarising before closing.

[I have read this]

## By station

Chest pain history(78 / 100 · Pass

Breaking bad news(64 / 100 · Pass

Prescribing review(Not scored

Keep practising

## Practise on your own

Nothing you do here is marked for the record.

[Self practice](SelfPractice.dc.html)

## Tab 2: Not released yet

Not released yetYour organisation has not released this result. When it is, we email you at the address your organisation holds for you.

## Tab 3: Acknowledge

[ ] I have read this

One way. After: "You read this on 6 Nov."
[Download PDF]

## Hire

The recruitment outcome is never shown to the candidate.
