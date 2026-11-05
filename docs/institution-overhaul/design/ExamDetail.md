# Exam detail

Source: `boards/ExamDetail.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

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

FY-OSCE{{ status }}

# Final-year OSCE

16 published stations · Marking scheme v3 · 4 sittings

[Schedule a sitting](ScheduleSitting.dc.html)

Available for scheduling

{{ toggleHelp }}

[]

## Stations
[Add station](NewStation.dc.html)

[
Chest pain in a 54-year-old
History and examination(Published v2](NewStation.dc.html)
[
Breaking bad news
Communication skills(Draft](NewStation.dc.html)
[
Diabetic foot review
History and examination(Published v1](NewStation.dc.html)

[See all 17 stations](Exams.dc.html)

## Sittings
[All sittings](Sittings.dc.html)

[
Summer finals
26 Nov · Formal exam(Scheduled](Sitting.dc.html)
[
March mock
Today · Formal exam(Running](Sitting.dc.html)

Marking scheme

St Mary's global rating

Version 3, published 2 Oct. 6 areas, rated Good, Fair or Poor.

[Open scheme](Exams.dc.html) [Change scheme](Exams.dc.html)

Station layouts (optional)

History and examination · Communication skills

[Manage layouts](Exams.dc.html)

Settings

3 min reading · 10 min consultation · 5 min break · Patient voice and feedback style

[Edit settings](NewExam.dc.html)

Retire or delete

[Retire exam]
[Delete exam]

Can't delete: this exam has sittings and recordings. Retire it instead, and its records stay.

What changed. The "Available for scheduling" switch replaces the Programmes tab's Retire, Activate and Reactivate buttons; that tab still exists on [Exams](Exams.dc.html) . Every field and setting is drawn on [Exam settings](ExamSettings.dc.html) ; the Retire and Delete confirms are on the Exams board.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/authoring/exams (exam row opens it)`

Who sees it
author_content

Owner agent
`content-owner` · prove with `verify-content` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/capabilities/authoring/sections/ExamsSection.tsx`

- `web/src/domains/assess/programmes/api.ts`

API calls (all exist; add no endpoint, change no schema)

`DELETE /api/v1/orgs/{org_slug}/exams/{exam_id}`Delete Org Exam
Now: web/src/app/(public)/exams/[exam]/page.tsx, web/src/app/sitemap.ts, web/src/capabilities/authoring/api/catalog.ts

`GET /api/v1/orgs/{org_slug}/exams`List Org Exams
Now: web/src/app/(public)/exams/[exam]/page.tsx, web/src/app/sitemap.ts, web/src/capabilities/authoring/api/catalog.ts

`GET /api/v1/orgs/{org_slug}/programmes`List Programmes
Now: web/src/capabilities/authoring/api/catalog.ts, web/src/domains/assess/NewSitting.tsx, web/src/domains/assess/api.ts

`PATCH /api/v1/orgs/{org_slug}/exams/{exam_id}`Update Org Exam
Now: web/src/app/(public)/exams/[exam]/page.tsx, web/src/app/sitemap.ts, web/src/capabilities/authoring/api/catalog.ts

`PATCH /api/v1/orgs/{org_slug}/programmes/{programme_id}`Update Programme
Now: web/src/capabilities/authoring/api/catalog.ts, web/src/domains/assess/NewSitting.tsx, web/src/domains/assess/api.ts

`POST /api/v1/orgs/{org_slug}/exams/{exam_id}/publish`Publish Org Exam
Now: web/src/capabilities/authoring/api/catalog.ts

`POST /api/v1/orgs/{org_slug}/exams/{exam_id}/retire`Retire Org Exam
Now: web/src/capabilities/authoring/api/catalog.ts

`POST /api/v1/orgs/{org_slug}/programmes`Add Programme
Now: web/src/capabilities/authoring/api/catalog.ts, web/src/domains/assess/NewSitting.tsx, web/src/domains/assess/api.ts

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.
