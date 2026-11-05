# Your sitting

Source: `boards/TraineeSitting.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Before it opens | 2. Station open | 3. Finished | 4. Joining | 5. Join refusals | 6. Stations and result

## Always on screen (menu, header, notes, build spec)

SM

St Mary's Medical School

Amara Okoye · Trainee

[My training](Trainee.dc.html)
[Practice sessions](Trainee.dc.html)
[Self practice](SelfPractice.dc.html)

[‹ All sittings](Trainee.dc.html)

Today 09:00

# March mock

Formal exam · 6 stations

(Live

[{{ t.label }}]
## Your stations

Station 1 · Chest pain history
Read this one back below. A finished station cannot be re-entered.
(Completed[Review station] [Station feedback](TraineeReview.dc.html)

Station 2 · Breaking bad news(Now

Station 3 · Abdominal examination(Not started
What changed: the candidate sees one step at a time: before it opens, your station, finished.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/trainee/sittings/[sittingId]`

Who sees it
Trainee

Owner agent
`institution-owner` · prove with `verify-institution` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/trainee/MySittingDetail.tsx`

- `web/src/domains/assess/trainee/JoinRoom.tsx`

- `web/src/domains/assess/trainee/LiveTurnBanner.tsx`

- `web/src/domains/assess/trainee/SlotReadingBrief.tsx`

API calls (all exist; add no endpoint, change no schema)

`POST /api/v1/me/circuits/{circuit_id}/join-token`Join Token
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

## Tab 1: Before it opens

Before you startYour station opens when your supervisor starts it. Go in straight away: the patient joins when reading time ends, and you need to be in the room by then.

## Check your microphone

We check it before you join. If your browser blocks it: "Allow it in the address bar, then try again."
[Test microphone]

## Tab 2: Station open

Station 2 of 6

## Your station is open

Breaking bad news

01:24

Reading
[Join]

## Reading brief

You are the FY1 on a medical ward. Mrs Jones's CT shows a mass. Explain the result and agree the next step.

## In the room

Your patient
Speaking

You
Microphone on

[Leave the room]
If you drop out we rejoin you by ourselves. Refusals are explained, e.g. "This circuit is not open yet. You will be let in when your supervisor starts it."

## Tab 3: Finished

Your result has been released[Read your result](TraineeResult.dc.html)

## Tab 4: Joining

## Microphone

Allow your microphone to join. Your browser blocked it.

No microphone found.

## Joining during reading

You join automatically while you read, so the patient is ready when it starts.

[Join] [Re-join] [Leave the room]

## Tab 5: Join refusals

This circuit is not open yet. It opens when your supervisor starts it.

That circuit is not on your list any more. Ask your organiser.

The voice service is not available right now. Try again in a minute.

Your access to this organisation has been withdrawn.

You are not on this circuit.

## Tab 6: Stations and result

## Your stations

Station 1 · Breaking bad news
Feedback ready

[Station feedback](TraineeReview.dc.html) [Review station](Trainee.dc.html)

Station 2
This station could not be marked; your school has been told.

Your result is out. [Read it](TraineeResult.dc.html)

Training reads "Your turn is live" and "Your turns".
