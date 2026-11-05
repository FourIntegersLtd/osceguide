# Station feedback

Source: `boards/TraineeReview.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Ready | 2. Not released | 3. Not marked

## Always on screen (menu, header, notes, build spec)

SM

St Mary's Medical School

Amara Okoye · Trainee

[My training](Trainee.dc.html)
[Practice sessions](Trainee.dc.html)
[Self practice](SelfPractice.dc.html)

[‹ Back](TraineeSitting.dc.html)

Your review

# Station feedback

Chest pain history · March mock

[{{ t.label }}]
▸ Build spec: how to build this screen

Route
`/app/[workspace]/trainee/reviews/[slotId]`

Who sees it
Trainee

Owner agent
`marking-owner` · prove with `verify-marking` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/trainee/MyReview.tsx`

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

## Tab 1: Ready

Overall

## Green (Pass

Clear structure and a safe plan. Ask about red flags earlier.

## By domain

History taking(Green

Communication(Amber

Clinical reasoning(Green

Completed 5 Nov, 14:20

## Tab 2: Not released

Not released yetYour result for this sitting has not been released, so the feedback on this station is not shared yet.

## Tab 3: Not marked

Not marked yetYour result is out, but the review of this station is not finished yet. It appears here when it is.
