# My training

Source: `boards/Trainee.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Home | 2. Practice history | 3. Banners | 4. Transcripts | 5. Debriefs | 6. Station record | 7. Station runner | 8. Practice sessions

## Always on screen (menu, header, notes, build spec)

SM

St Mary's Medical School

Amara Okoye · Trainee

[My training](Trainee.dc.html)
[Practice sessions](Trainee.dc.html)
[Self practice](SelfPractice.dc.html)

St Mary's Medical School

# Hello, Amara.

(Live

[{{ t.label }}]
What changed: the menu is My training, Practice sessions and Self practice. These screens are today's, drawn so none is missed.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/trainee`

Who sees it
Trainee

Owner agent
`institution-owner` · prove with `verify-institution` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/trainee/TraineeHome.tsx`

- `web/src/domains/assess/trainee/StationRecord.tsx`

API calls (all exist; add no endpoint, change no schema)

`GET /api/v1/me/sittings`Read My Sittings
Now: web/src/domains/assess/trainee/MySittingDetail.tsx, web/src/domains/assess/trainee/api.ts, web/src/surfaces/assess/surface.ts

`GET /api/v1/me/sittings/stream`Stream My Sittings
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

## Tab 1: Home

Today

## Your station is open

March mock · Circuit 1. Go in and read the brief. The patient joins when the reading time ends.

[Go in](TraineeSitting.dc.html)

## Your sittings

[March mock
Examination · 1 of 6 stations completed · Today · Your station is open
(Open now](TraineeSitting.dc.html) [Year 3 practice round
Practice circuit · 12 Nov · Not started
](TraineeSitting.dc.html)

## Past sittings

[Year 4 mock
Examination · Finished: open it for your result and feedback
(Result released](TraineeResult.dc.html)

## Practise

[Self practice
From your organisation
](SelfPractice.dc.html) [Practice sessions
Practice sets you work through, station by station
] [Practice history
Past attempts, transcripts and debriefs
]

## Tab 2: Practice history

## Transcripts
‹input: Search by exam or session type›

4 NovFINALS · Self practice[View details]

28 OctFINALS · Exam station[View details]

## Debriefs

Debrief session
4 Nov, 18:10
Narrative summary, key insights, action plan

Your debrief has ended. Athena is writing its summary, and it will appear here in a minute.

## Tab 3: Banners

You were sent to a station on March mock. [Open it.](TraineeSitting.dc.html)

Your turn is live. Join now.

Empty: "You are not booked on anything yet." Hire: "My assessments".

March mock
Continue: Station 2

Feb mock
Finished · Read your result

## Tab 4: Transcripts

## Transcripts

A transcript is saved each time you complete a consultation.
‹input: Search by exam or session type›
4 Nov
FINALS · Mock station

[View details]

1 Nov
FINALS · Self practice

[View details]

Empty: "No transcripts yet". Detail: "Transcript details", "Nothing was transcribed", "This transcript is still being delivered."

## Tab 5: Debriefs

## Debriefs

Each time you talk a consultation through with Athena, its summary is kept here.

Debrief session
4 Nov

Empty: "No debriefs yet. Start a debrief from a station you have already sat."

## Debrief details
Narrative summary
You explored her concerns well…
Key insights
01 · Signposting
Action plan
01 · Summarise before the plan

## Debrief session

Speak naturally to discuss your performance
[Start voice debrief]
Athena is busy. You are number 2 in line.
[End debrief]
Your debrief has ended. Athena is writing its summary…

We could not write a summary.

## Tab 6: Station record

## Your consultation

Station record
Feedback
Data gathering
Met the pass line

Management
Below the pass line

Transcript

## States

Your feedback is being prepared. Marking a consultation takes a minute or two.

This attempt could not be marked.

No feedback recorded

## Tab 7: Station runner

## Station 1 of 3 · Attempts: 1/3

1Reading time

2Consultation

3Management

4Feedback

[Start consultation]
Connecting you to the patient…
[Captions] [End Consultation]

## Runner boxes

Ready to start?

You have a consultation in progress

[Resume] [Start again]

End consultation now?

[End consultation] [Keep going]

Leave this consultation?

[End and leave] [Stay]

Time up

Marking your consultation
Marking usually takes one to three minutes.

We could not mark this consultation

[Check again] [Continue to session summary]

Report a problem
What is wrong? (optional)

[Send report]

## Tab 8: Practice sessions

## FINALS sessions
[New session]
Session 4 Nov
(Completed (Feedback

[Edit] [Delete]

Empty: "No sessions yet. Create your first session to practise with an AI patient. It takes about 12 minutes per station."

## Session

For each station: 2 minutes reading, then 8 minutes with the patient
[Start session]
Sit them back to back. Feedback for each station is prepared while you sit the next.

Station 1
1 of 3 attempted

[Review last attempt] [Start new attempt]

## Session completed

Well done

Station 1
Feedback ready

Station 2
Marking

Station 3
Not attempted

[Review session] [New session]
