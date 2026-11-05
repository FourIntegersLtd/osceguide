# New exam

Source: `boards/NewExam.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

## Always on screen (menu, header, notes, build spec)

[Close](Exams.dc.html) New exam

Your progress is saved after each step

[{{ s.mark }}{{ s.label }}]

Step 1 of 4

# Name your exam

This is what supervisors and trainees will see on every sitting.

Exam name
‹input: Paediatrics block›

Short code
‹input: PAED›
Letters, numbers and dashes. It can't be the same as another of your exams.

Step 2 of 4

# How will it be marked?

The marking scheme lists the areas reviewers rate and how. You can change it later as a new version.

[{{ o.title }}{{ o.body }}]

Opens the scheme builder. When you publish the scheme, you come straight back here.

Step 3 of 4

# Timings and settings

These are the defaults for every circuit. You can change them per circuit when you schedule.

Reading time
‹input: 3 min›
1 to 30

Consultation
‹input: 10 min›
1 to 180

Break
‹input: 5 min›
1 to 60, formal exams

▸ More settings

Patient voice, feedback style and the AI writing setup. The same options as today's exam settings.

Step 4 of 4

# Ready to publish

Publishing makes the exam available for scheduling. Add stations next.

ExamPaediatrics block · PAED

Marking schemeCopy of OSCE Guide global rating, v1

Timings3 min reading · 10 min consultation · 5 min break

Available for scheduling(On after publishing

If a step fails, the exam is kept as it is and this screen says which step to retry. Nothing is half made.

[Back]
[Continue]
[Publish exam](ExamDetail.dc.html)

What changed. Today an exam, its marking scheme and its programme are made on three tabs; here one sheet makes all three. Step 3 is the full form, drawn on the [Exam settings](ExamSettings.dc.html) board. Adopting an OSCE Guide exam is on [Adopt an exam](AdoptExam.dc.html) .

▸ Build spec: how to build this screen

Route
`/app/[workspace]/authoring/exams (New exam sheet)`

Who sees it
author_content

Owner agent
`content-owner` · prove with `verify-content` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/capabilities/authoring/sections/ExamsSection.tsx`

- `web/src/capabilities/authoring/sections/ExamFields.tsx`

- `web/src/capabilities/authoring/sections/ExamSettingsFields.tsx`

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

`POST /api/v1/orgs/{org_slug}/exams`Create Org Exam
Now: web/src/app/(public)/exams/[exam]/page.tsx, web/src/app/sitemap.ts, web/src/capabilities/authoring/api/catalog.ts

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
