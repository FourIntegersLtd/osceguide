# Self practice

Source: `boards/SelfPractice.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Screen | 2. Not available

## Always on screen (menu, header, notes, build spec)

SM

St Mary's Medical School

Amara Okoye · Trainee

[My training](Trainee.dc.html)
[Practice sessions](Trainee.dc.html)
[Self practice](SelfPractice.dc.html)

[{{ t.label }}]
What changed: none.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/trainee/practice and /stations/[stationId]/practise`

Who sees it
Trainee

Owner agent
`attempt-engine-owner` · prove with `verify-attempt-engine` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/trainee/SelfPractice.tsx`

- `web/src/domains/assess/trainee/SelfPracticeStation.tsx`

- `web/src/domains/assess/trainee/practisableStation.ts`

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

## Tab 1: Screen

Practise

# Self practice

Your organisation's stations. Nothing here is marked for the record.

‹input: Search stations›

(FINALSChest pain history[Practise]

(FINALSBreaking bad news[Practise]

(FINALSHeadache history[Practise]

Opens the practice station (reading, consultation, feedback, transcript, debrief). Empty: "No published stations yet. Your organisation has not added any stations yet. Ask your administrator when they will be ready." Which exams a trainee may practise is set by an admin under People › Exam access.

## Tab 2: Not available

## This station is not available

It may have been withdrawn, is not published yet, or belongs to another organisation.
[Back to practice]

On every self-practice station: "Nothing here is marked for the record."
