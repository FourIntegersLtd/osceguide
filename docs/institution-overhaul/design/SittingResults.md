# Sitting results

Source: `boards/SittingResults.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Results | 2. Release all | 3. Decision form | 4. Released and supervisor | 5. Review order and exports

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

[{{ t.label }}]
What changed: none in the decision; the release confirm and refusals are drawn here in full.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/sittings/[sittingId]/results`

Who sees it
sign_off_results

Owner agent
`marking-owner` · prove with `verify-marking` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/results/Results.tsx`

- `web/src/domains/assess/results/CandidateDecision.tsx`

- `web/src/domains/assess/results/ReleaseAll.tsx`

- `web/src/domains/assess/results/CohortRanking.tsx`

- `web/src/domains/assess/results/ReadoutExport.tsx`

- `web/src/domains/assess/results/CandidateCard.tsx`

API calls (all exist; add no endpoint, change no schema)

`GET /api/v1/orgs/{org_slug}/reporting`Read Org Reporting
Now: web/src/domains/assess/index.ts, web/src/domains/assess/reporting/Reporting.tsx, web/src/domains/assess/reporting/api.ts

`GET /api/v1/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/decision`Read Decision
Now: web/src/domains/assess/results/api.ts

`GET /api/v1/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/result-preview`Read Result Preview
Now: web/src/domains/assess/results/api.ts

`GET /api/v1/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/result.pdf`Read Result Pdf
Now: web/src/domains/assess/results/api.ts

`GET /api/v1/orgs/{org_slug}/sittings/{sitting_id}/cohort`Read Cohort Summary
Now: web/src/domains/assess/results/api.ts

`GET /api/v1/orgs/{org_slug}/sittings/{sitting_id}/readout`Read Sitting Readout
Now: web/src/domains/assess/results/api.ts

`GET /api/v1/orgs/{org_slug}/sittings/{sitting_id}/report`Read Sitting Report
Now: web/src/domains/assess/results/api.ts

`GET /api/v1/orgs/{org_slug}/sittings/{sitting_id}/report.csv`Read Sitting Report Csv
Now: web/src/domains/assess/results/api.ts

`POST /api/v1/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/decision/release`Release
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/decision/sign-off`Sign Off
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/sittings/{sitting_id}/decisions/release`Release Many
Now: web/src/domains/assess/results/api.ts

`PUT /api/v1/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/decision`Save Decision
Now: web/src/domains/assess/results/api.ts

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.

## Tab 1: Results

[‹ Sitting](Sitting.dc.html)

March mock

# Results

40 of 48 stations marked · 0 of 8 released

[Download CSV]

Passed3

Failed1

Inconclusive0

Withheld0

Undecided4

Awaiting marking2

ScheduleDate set

CircuitsCandidates sat

RunAll finished

Mark40 of 48 marked

Decide4 of 8 decided

Release0 of 8 released

3 results signed off and not yet released.

## Candidates to release
Untick anyone to hold their result back.

[x] All 3

[x] Amara Okoye

[x] Dev Shah

[x] Esme Lowe

[Release 3 signed-off results]

Review order

8 candidates, with unfinished reviews first, then the weakest results.

[Export readout]

1. Chloe Imran
4/6 stations · 67% complete
(Urgent review

2. Ben Hart
6/6 stations · 48/100 · 100% complete
(High priority

CandidateScoreOutcomeStatus

AO

Amara Okoye

6 of 6 stations marked · overall Green

72/100(Pass(Signed off[Open]

BH

Ben Hart

6 of 6 stations marked

48/100Not decided(Marked[Open]

CI

Chloe Imran

4 of 6 stations marked

Not assessedNot decided(Not marked[Open]

## Ben Hart · the decision
(Draft Revision 1

Marked6 of 6 marked

Reviewed6 of 6 reviewed

DecidedNot decided

Signed offNot signed off

ReleasedNot released

Stations

[Chest pain history
Circuit 2 · completed
(Green](SlotReview.dc.html) [Breaking bad news
Circuit 2 · completed
(Awaiting review](SlotReview.dc.html)

Outcome

[Pass · Met the standard.] [Fail · Did not meet the standard.] [Inconclusive · Not enough was assessed to decide.] [Withheld · Decided, but held back, for example during an appeal.]

Suggested from the marks: 2 of 6 stations passed. You decide.

Recruitment outcome (hire only)

‹select:
Not recorded |

Pending |

Hired |

Reserve list |

Not hired |

Withdrawn |
›

Whether you are taking this candidate on. The candidate does not see it.

Rationale

‹textarea: Why this outcome, in the words you would use to a candidate or an appeal panel.›

Before this can be signed offWrite down the reason, so anyone can see why this was decided later.

[Preview what they'll see] [Save draft] [Sign off]

Signed off: the form locks, "Back to draft" appears, and "Result PDF" appears once released. Sign-off covers the marks as they were; a re-mark needs a new sign-off. A withheld or inconclusive outcome is never sent.

## Tab 2: Release all

## Candidates to release

Untick anyone to hold their result back.

[x] Amara Okoye

Pass · signed off

[x] Ben Hart

Fail · signed off

[ ] Chloe Imran

Not signed off

[Release 2 signed-off results]
1 released, 1 refused. Chloe Imran: not signed off yet.

## Tab 3: Decision form

## Decision for Amara Okoye

Outcome

‹select:
Pass |

Fail |

Inconclusive |

Withheld |
›

Hire shows "Recruitment outcome".

‹textarea: Why this outcome, in the words you would use to a candidate or an appeal panel.›

Before this can be signed off

Every station marked · a rationale written

[Save draft] [Sign off] [Back to draft] [Preview what they'll see]

This decision has changed since you loaded it. [Load the latest version]

Sign-off covers the marks as they were at the time. A later remark does not change it.

## Tab 4: Released and supervisor

## Released

Released 14 Mar. Once released, a decision cannot be edited. Any correction is saved as a new version.
[Result PDF]

## Supervisor view

An institution administrator records, signs off and releases the decision.

## Tab 5: Review order and exports

## Review order

Ben Hart
(Urgent review

Chloe Imran
(High priority

Dev Shah
(Standard

Esme Lowe
(Low priority

[Export readout]
Formal exam only.

## Outcomes

Passed
3

Failed
1

Inconclusive
0

Withheld
0

Undecided
1

Awaiting marking
0

[Export CSV]

## Dialog: release

## Email 3 candidates their result?

Each can read their outcome as soon as it is released, and a released result is final.

[Cancel] [Release](TraineeResult.dc.html)

## Dialog: preview

## Result preview

Preview of the last saved version. The candidate cannot see this until it is released.

Outcome

## Fail, 48.0 / 100

Did not show safe prioritisation in two stations.

[Close]

## Dialog: rel

## Email 2 candidates their result?

Each can read their outcome as soon as it is released, and a released result is final.

[Cancel] [Release]

## Dialog: back

## Back to draft?

The sign-off is removed so you can change the decision. Nothing has been released.

[Cancel] [Back to draft]

## Dialog: prev

## Result preview

What Amara Okoye will read once released.

Pass
By station: 1 Pass · 2 Pass · 3 Pass

[Close]
