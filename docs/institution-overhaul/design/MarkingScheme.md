# Marking scheme builder

Source: `boards/MarkingScheme.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

## Always on screen (menu, header, notes, build spec)

[Close](NewExam.dc.html) Marking scheme(Draft v4

[Save draft] [Publish and go back](NewExam.dc.html)

Exams › Marking schemes

# St Mary's global rating

How a station is marked, and what the candidate's feedback looks like. Publishing makes a new version; sittings already marked keep the version they used.

[{{ t.label }}]

## Areas marked
Each domain is rated on its own

Data gatheringWeight 1[Edit]

Clinical managementWeight 1[Edit]

Interpersonal skillsWeight 1[Edit]

Safety nettingWeight 1[Edit]

[Add an area]

## Marking instructions

Written for the AI marker and for supervisors. Draft them for me from the areas above, then edit.

‹textarea: ›Credit open questions early. Safety netting must name a time frame…

## Pacing, in seconds

Introduction ends
‹input: 60›

History ends
‹input: 420›

Safety-net window
‹input: 90›

## Grades

(GoodMeets the standard with no prompting2

(FairMostly there, minor gaps1

(PoorUnsafe or missing0

[Add grade]

## Station total and pass line

Out of
‹input: 8›

Pass line
‹input: 5›

Domain pass line
‹input: 1›

[x] Every domain must pass too

Bands (optional): Clear pass, Borderline, Fail, each from a score.

This was the feedback template. It now lives here, with the marking it describes.

## What the candidate sees

Overall result and band(Shown

Score per area(Shown

What went well(Shown

What to work on(Shown

Transcript quotes(Hidden

[Add a field]

## Tone

‹select:
Supportive and direct |

Formal examiner |

Brief |
›

Examiner layout: what the supervisor sees when reviewing is set alongside.

## Trial mark

Mark a real attempt or a pasted transcript with this draft, before anyone else does.

Trial source

‹select:
An attempt: Aisha Bello, Chest pain, 2 Nov |

Paste a transcript |
›

[Run trial mark]

Result: 6 of 8, Clear pass. Safety netting rated Fair: "no time frame given".

## Versions

v4Draft, edited today(Draft

v3Published 2 Oct · used by Final-year OSCE(Live

v2Published 4 Sep(Old

## Problems

None. Publishing is blocked while any are listed here, and each says what to fix.

Preview: candidate feedback

Chest pain in a 54-year-old(Clear pass

6 of 8

Data gatheringGood

Clinical managementGood

Interpersonal skillsFair

Safety nettingFair

What to work on

Give a clear time frame when you safety net: "if it is no better in 48 hours…"

▸ Build spec: how to build this screen

Route
`/app/[workspace]/authoring/rubrics/[rubricId]/versions/[version]`

Who sees it
author_content

Owner agent
`marking-owner` · prove with `verify-marking` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/capabilities/authoring/rubrics/RubricBuilderScreen.tsx`

- `web/src/capabilities/authoring/rubrics/RubricBuilder.tsx`

- `web/src/capabilities/authoring/rubrics/TrialPanel.tsx`

- `web/src/capabilities/authoring/rubrics/PreviewPane.tsx`

API calls (all exist; add no endpoint, change no schema)

`GET /api/v1/orgs/{org_slug}/rubrics`List Org Rubrics
Now: web/src/app/app/[workspace]/authoring/feedback-templates/[templateId]/versions/[version]/page.tsx, web/src/app/app/[workspace]/authoring/feedback-templates/new/page.tsx, web/src/app/app/[workspace]/authoring/page.tsx

`GET /api/v1/orgs/{org_slug}/rubrics/starting-points`Org Rubric Starting Points
Now: web/src/capabilities/authoring/api/rubrics.ts

`GET /api/v1/orgs/{org_slug}/rubrics/trial-candidates`List Org Trial Candidates
Now: web/src/capabilities/authoring/api/rubrics.ts

`GET /api/v1/orgs/{org_slug}/rubrics/{rubric_id}`Read Org Rubric
Now: web/src/app/app/[workspace]/authoring/feedback-templates/[templateId]/versions/[version]/page.tsx, web/src/app/app/[workspace]/authoring/feedback-templates/new/page.tsx, web/src/app/app/[workspace]/authoring/page.tsx

`PATCH /api/v1/orgs/{org_slug}/rubrics/{rubric_id}`Rename Org Rubric
Now: web/src/app/app/[workspace]/authoring/feedback-templates/[templateId]/versions/[version]/page.tsx, web/src/app/app/[workspace]/authoring/feedback-templates/new/page.tsx, web/src/app/app/[workspace]/authoring/page.tsx

`PATCH /api/v1/orgs/{org_slug}/rubrics/{rubric_id}/versions/{version}`Edit Org Version
Now: web/src/capabilities/authoring/api/rubrics.ts

`POST /api/v1/orgs/{org_slug}/rubrics`Create Org Rubric
Now: web/src/app/app/[workspace]/authoring/feedback-templates/[templateId]/versions/[version]/page.tsx, web/src/app/app/[workspace]/authoring/feedback-templates/new/page.tsx, web/src/app/app/[workspace]/authoring/page.tsx

`POST /api/v1/orgs/{org_slug}/rubrics/copy`Copy Org Rubric
Now: web/src/capabilities/authoring/api/rubrics.ts

`POST /api/v1/orgs/{org_slug}/rubrics/draft-instructions`Draft Org Rubric Instructions
Now: web/src/capabilities/authoring/api/rubrics.ts, web/src/capabilities/authoring/rubrics/draftInstructions.ts

`POST /api/v1/orgs/{org_slug}/rubrics/preview`Preview Org Rubric
Now: web/src/capabilities/authoring/api/rubrics.ts, web/src/capabilities/authoring/rubrics/problems.ts, web/src/capabilities/authoring/rubrics/useRubricDraft.ts

`POST /api/v1/orgs/{org_slug}/rubrics/{rubric_id}/versions`Add Org Version
Now: web/src/capabilities/authoring/api/rubrics.ts

`POST /api/v1/orgs/{org_slug}/rubrics/{rubric_id}/versions/{version}/archive`Archive Org Version
Now: web/src/capabilities/authoring/api/rubrics.ts

`POST /api/v1/orgs/{org_slug}/rubrics/{rubric_id}/versions/{version}/publish`Publish Org Version
Now: web/src/capabilities/authoring/api/rubrics.ts

`POST /api/v1/orgs/{org_slug}/rubrics/{rubric_id}/versions/{version}/trial`Trial Org Rubric Version
Now: web/src/capabilities/authoring/api/rubrics.ts

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.
