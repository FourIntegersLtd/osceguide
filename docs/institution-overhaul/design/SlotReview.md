# Mark this station

Source: `boards/SlotReview.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Supervisor: your marks | 2. Admin: admin's review | 3. Marking states | 4. Transcript and agreement

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

[‹ Circuit 1 · Amara Okoye](CircuitReview.dc.html)

Amara Okoye · Station 2 · Breaking bad news

# Mark this station

The automatic marking, your marks and the admin's review.

Candidate 1 of 8[Previous] [Next candidate]

Automatic markingReady

Your marksDraft

Rate each area, then submit your marks.

[{{ t.label }}]
What changed: none in the marking itself; the page names whose turn it is (supervisor's marks, then the admin's review).

▸ Build spec: how to build this screen

Route
`/app/[workspace]/slots/[slotId]/review`

Who sees it
Assigned reviewers and the circuit's supervisor

Owner agent
`marking-owner` · prove with `verify-marking` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/SlotReview.tsx`

- `web/src/domains/assess/results/MarkingPanel.tsx`

- `web/src/domains/assess/results/ReviewFields.tsx`

- `web/src/domains/assess/results/GpLeadReview.tsx`

- `web/src/domains/assess/results/slotReviewSteps.ts`

API calls (all exist; add no endpoint, change no schema)

`DELETE /api/v1/orgs/{org_slug}/slots/{slot_id}/gp-lead-review`Withdraw Gp Lead Review
Now: web/src/domains/assess/results/api.ts

`DELETE /api/v1/orgs/{org_slug}/slots/{slot_id}/reviews/{review_id}`Withdraw Review
Now: web/src/domains/assess/api.ts, web/src/domains/assess/results/api.ts

`GET /api/v1/me/slots/{slot_id}/brief`Read Slot Brief
Now: web/src/domains/assess/trainee/SlotReadingBrief.tsx, web/src/domains/assess/trainee/api.ts

`GET /api/v1/me/slots/{slot_id}/review`Read My Slot Review
Now: web/src/domains/assess/trainee/api.ts

`GET /api/v1/orgs/{org_slug}/slots/{slot_id}/gp-lead-review`Read Gp Lead Review
Now: web/src/domains/assess/results/api.ts

`GET /api/v1/orgs/{org_slug}/slots/{slot_id}/reviews`List Slot Reviews
Now: web/src/domains/assess/api.ts, web/src/domains/assess/results/api.ts

`GET /api/v1/orgs/{org_slug}/slots/{slot_id}/reviews/mine`Read My Review
Now: web/src/domains/assess/api.ts

`POST /api/v1/orgs/{org_slug}/slots/{slot_id}/marking/retry`Retry Slot Marking
Now: web/src/domains/assess/api.ts

`PUT /api/v1/orgs/{org_slug}/slots/{slot_id}/gp-lead-review`Save Gp Lead Review
Now: web/src/domains/assess/results/api.ts

`PUT /api/v1/orgs/{org_slug}/slots/{slot_id}/reviews/mine`Submit My Review
Now: web/src/domains/assess/api.ts

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.

## Tab 1: Supervisor: your marks

## Your marks
(Draft

History taking (Required

Machine: Green

GreenAmberRed

Communication (Required

Machine: Amber

GreenAmberRed

Clinical reasoning (Required

Machine: Green

GreenAmberRed

Notes

‹textarea: What you saw, in the words you would say to them.›

Still to rate before completing: Clinical reasoning.

[Withdraw draft] [Save draft] [Submit review](CircuitReview.dc.html)

## Automatic marking

History taking: Green · Communication: Amber · Clinical reasoning: Green. Overall 68 / 100, pass.

When marking failed: "Automatic marking failed. Retry it, or mark this station without it." [Retry marking]

## What was said

Everything said in the consultation. The marks are shown separately.

[Load the transcript] [Download]

## What the reviewers agreed

1 completed review · 1 still in progress

(Agreed: Green(Pass

Where reviewers disagreed, the lower rating is the one shown.

## Tab 2: Admin: admin's review

## Admin's review
(Draft Revision 2

One overall mark for the station. This is the mark that counts.

History taking (Required

Machine: Green

GreenAmberRed

‹input: Why this rating for History taking›

Communication (Required

Machine: Amber

GreenAmberRed

‹input: Why this rating for Communication›

Clinical reasoning (Required

Machine: Green

GreenAmberRed

‹input: Why this rating for Clinical reasoning›

Overall

GreenAmberRed

Notes

‹textarea: What you saw, in the words you would say to them.›

[Save draft] [Complete review]

Rate every required area before completing the review, so candidates never see a half-finished one. A completed admin review stays editable (Save changes).

## Automatic marking

History taking: Green · Communication: Amber · Clinical reasoning: Green. Overall 68 / 100, pass.

When marking failed: "Automatic marking failed. Retry it, or mark this station without it." [Retry marking]

## What was said

Everything said in the consultation. The marks are shown separately.

[Load the transcript] [Download]

## What the reviewers agreed

1 completed review · 1 still in progress

(Agreed: Green(Pass

Where reviewers disagreed, the lower rating is the one shown.

## Tab 3: Marking states

## Marking

The AI mark is on its way. This page updates on its own.

## Could not be marked

This station could not be marked.
[Retry marking]

## Not your circuit

You are not named on this station's circuit, so its marking is hidden from you.

## Conflict

Another reviewer saved since you opened this. Load theirs before saving.

## Tab 4: Transcript and agreement

## Transcript
[Load transcript] [Download]
Only the supervisor named on the circuit can read it.

## Reviewers

Dr Patel
Pass

Ms Clarke
Pass

Reviewers agree.

## Candidate stepper

[‹ Previous candidate] [Next candidate ›]

Shown when opened from Results.
