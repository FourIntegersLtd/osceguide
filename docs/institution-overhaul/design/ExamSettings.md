# Exam settings

Source: `boards/ExamSettings.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Edit exam | 2. Create exam | 3. Guide lines by state

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

[‹ Exams](Exams.dc.html)

Final MB OSCE

# Exam settings

Every setting an exam has: its timings, how it is marked, and what trainees get after a station.

[{{ t.label }}]
Same fields as today's Create exam and Edit exam dialogs. What changed: it opens as a page from the exam, and step 3 of New exam uses the same form.

▸ Build spec: how to build this screen

Route
`dialog today (Create exam / Edit exam); page or sheet in the redesign`

Who sees it
author_content

Owner agent
`content-owner` · prove with `verify-content` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/capabilities/authoring/sections/ExamFields.tsx`

- `web/src/capabilities/authoring/sections/ExamSettingsFields.tsx`

- `web/src/capabilities/authoring/sections/examSteps.ts`

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

## Tab 1: Edit exam

Pick marking schemeChosen

PublishDraft

Publish this exam to run sittings against it.

Code
‹input: finals›

Name
‹input: e.g. Final MB OSCE›

Reading time (seconds)
‹input: 120›

Station time (seconds)
‹input: 600›

Attempts per station
‹input: 3›

Marking scheme version

‹select:
None yet |

*Consultation skills · v2 |
›

▸ Exam settings

Date label
‹input: Exam date›

After a station

[x] Tutor debrief

[x] Practise as the patient

Help dock

[x] Find screens

[ ] Answer from the knowledge base

Other

[ ] Show examiner tips while marking

[ ] Email people waiting for a peer partner

Station writing prompt

‹textarea: Blank uses the built-in prompt (generic.station).›

Condition summary prompt

‹textarea: Blank uses the built-in prompt (generic.summary).›

Blog prompt

‹textarea: Blank uses the built-in prompt (generic.blog).›

Partner-pilot status is set by OSCE Guide staff, not from here.

[Cancel](Exams.dc.html) [Save]

## Tab 2: Create exam

The code is unique within this organisation only, so two schools may both have a finals.

Code
‹input: e.g. finals›

Name
‹input: e.g. Final MB OSCE›

Reading time (seconds)
‹input: 120›

Station time (seconds)
‹input: 600›

Attempts per station
‹input: 3›

Marking scheme version

‹select:
None yet |

Consultation skills · v2 |
›

▸ Exam settings

Date label
‹input: Exam date›

After a station

[x] Tutor debrief

[x] Practise as the patient

Help dock

[x] Find screens

[ ] Answer from the knowledge base

Other

[ ] Show examiner tips while marking

[ ] Email people waiting for a peer partner

Station writing prompt

‹textarea: Blank uses the built-in prompt (generic.station).›

Condition summary prompt

‹textarea: Blank uses the built-in prompt (generic.summary).›

Blog prompt

‹textarea: Blank uses the built-in prompt (generic.blog).›

Partner-pilot status is set by OSCE Guide staff, not from here.

[Cancel](Exams.dc.html) [Create exam]

## Tab 3: Guide lines by state

Live
Live. Add a programme for it so people can take it.

Retired
Retired. It is no longer offered for new sittings.

No scheme
Pick a marking scheme, then publish.

Marking schemes could not be loaded
