# Exams

Source: `boards/Exams.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Exams | 2. Stations | 3. Marking schemes | 4. Station layouts | 5. Programmes | 6. Empty and read-only states

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

Organise

# Exams

Everything you examine with: the exams themselves, their stations, how they are marked, the layout a station follows, and which exams are offered for scheduling.

[{{ t.label }}]
What changed: today's Build page (title "Authoring") becomes Exams, with Exams as the first tab. The separate Stations and Programmes nav items go; they are tabs here and their URLs still work.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/authoring/[section] (sections: exams, stations, rubrics, station-templates, programmes)`

Who sees it
Anyone with author_content writes; others read only

Owner agent
`content-owner` · prove with `verify-content` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/capabilities/authoring/Authoring.tsx`

- `web/src/capabilities/authoring/sections.ts`

- `web/src/capabilities/authoring/sections/ExamsSection.tsx`

- `web/src/capabilities/authoring/sections/StationsSection.tsx`

- `web/src/capabilities/authoring/sections/StationsTable.tsx`

- `web/src/capabilities/authoring/sections/RubricsSection.tsx`

- `web/src/capabilities/authoring/sections/StationTemplatesSection.tsx`

- `web/src/capabilities/authoring/sections/ProgrammesSection.tsx`

- `web/src/capabilities/authoring/parts/ListCard.tsx`

- `web/src/capabilities/authoring/parts/StatusPills.tsx`

API calls (all exist; add no endpoint, change no schema)

`DELETE /api/v1/orgs/{org_slug}/exams/{exam_id}`Delete Org Exam
Now: web/src/app/(public)/exams/[exam]/page.tsx, web/src/app/sitemap.ts, web/src/capabilities/authoring/api/catalog.ts

`DELETE /api/v1/orgs/{org_slug}/station-templates/{template_id}/versions/{version}`Delete Station Template Version
Now: web/src/capabilities/authoring/api/templates.ts

`DELETE /api/v1/orgs/{org_slug}/stations/{station_id}/versions/{version}`Delete Version
Now: web/src/capabilities/authoring/api/stations.ts, web/src/capabilities/authoring/sections/StationVersionHistory.tsx, web/src/capabilities/stations/api.ts

`GET /api/v1/exams`List Exams
Now: capabilities/stations/api.ts

`GET /api/v1/stations`Browse Library
Now: capabilities/stations/api.ts

`GET /api/v1/stations/{station_id}`Read Library Station
Now: web/src/app/app/[workspace]/authoring/stations/new/page.tsx, web/src/app/app/[workspace]/stations/page.tsx, web/src/app/staff/authoring/page.tsx

`GET /api/v1/stations/{station_id}/versions`Station Version History
Now: web/src/capabilities/authoring/api/stations.ts, web/src/capabilities/authoring/sections/StationVersionHistory.tsx, web/src/capabilities/stations/api.ts

`GET /api/v1/orgs/{org_slug}/exams`List Org Exams
Now: web/src/app/(public)/exams/[exam]/page.tsx, web/src/app/sitemap.ts, web/src/capabilities/authoring/api/catalog.ts

`GET /api/v1/orgs/{org_slug}/exams/catalog`List Platform Catalogue
Now: web/src/domains/assess/programmes/api.ts

`GET /api/v1/orgs/{org_slug}/programmes`List Programmes
Now: web/src/capabilities/authoring/api/catalog.ts, web/src/domains/assess/NewSitting.tsx, web/src/domains/assess/api.ts

`GET /api/v1/orgs/{org_slug}/rubrics`List Org Rubrics
Now: web/src/app/app/[workspace]/authoring/feedback-templates/[templateId]/versions/[version]/page.tsx, web/src/app/app/[workspace]/authoring/feedback-templates/new/page.tsx, web/src/app/app/[workspace]/authoring/page.tsx

`GET /api/v1/orgs/{org_slug}/rubrics/starting-points`Org Rubric Starting Points
Now: web/src/capabilities/authoring/api/rubrics.ts

`GET /api/v1/orgs/{org_slug}/rubrics/trial-candidates`List Org Trial Candidates
Now: web/src/capabilities/authoring/api/rubrics.ts

`GET /api/v1/orgs/{org_slug}/rubrics/{rubric_id}`Read Org Rubric
Now: web/src/app/app/[workspace]/authoring/feedback-templates/[templateId]/versions/[version]/page.tsx, web/src/app/app/[workspace]/authoring/feedback-templates/new/page.tsx, web/src/app/app/[workspace]/authoring/page.tsx

`GET /api/v1/orgs/{org_slug}/station-templates`List Station Templates
Now: web/src/capabilities/authoring/api/templates.ts, web/src/capabilities/authoring/templates/paths.ts, web/src/domains/assess/dashboard/support.ts

`GET /api/v1/orgs/{org_slug}/stations`List Stations
Now: web/src/app/app/[workspace]/authoring/stations/new/page.tsx, web/src/app/app/[workspace]/stations/page.tsx, web/src/app/staff/authoring/page.tsx

`PATCH /api/v1/orgs/{org_slug}/exams/{exam_id}`Update Org Exam
Now: web/src/app/(public)/exams/[exam]/page.tsx, web/src/app/sitemap.ts, web/src/capabilities/authoring/api/catalog.ts

`PATCH /api/v1/orgs/{org_slug}/programmes/{programme_id}`Update Programme
Now: web/src/capabilities/authoring/api/catalog.ts, web/src/domains/assess/NewSitting.tsx, web/src/domains/assess/api.ts

`PATCH /api/v1/orgs/{org_slug}/rubrics/{rubric_id}`Rename Org Rubric
Now: web/src/app/app/[workspace]/authoring/feedback-templates/[templateId]/versions/[version]/page.tsx, web/src/app/app/[workspace]/authoring/feedback-templates/new/page.tsx, web/src/app/app/[workspace]/authoring/page.tsx

`PATCH /api/v1/orgs/{org_slug}/rubrics/{rubric_id}/versions/{version}`Edit Org Version
Now: web/src/capabilities/authoring/api/rubrics.ts

`PATCH /api/v1/orgs/{org_slug}/station-templates/{template_id}/versions/{version}`Edit Station Template Version
Now: web/src/capabilities/authoring/api/templates.ts

`PATCH /api/v1/orgs/{org_slug}/stations/{station_id}/versions/{version}`Edit Version
Now: web/src/capabilities/authoring/api/stations.ts, web/src/capabilities/authoring/sections/StationVersionHistory.tsx, web/src/capabilities/stations/api.ts

`PATCH /api/v1/orgs/{org_slug}/stations/{station_id}/versions/{version}/brief`Edit Brief
Now: web/src/capabilities/authoring/api/stations.ts

`POST /api/v1/orgs/{org_slug}/exams/import`Import Platform Exam
Now: web/src/domains/assess/programmes/api.ts

`POST /api/v1/orgs/{org_slug}/exams/{exam_id}/publish`Publish Org Exam
Now: web/src/capabilities/authoring/api/catalog.ts

`POST /api/v1/orgs/{org_slug}/exams/{exam_id}/retire`Retire Org Exam
Now: web/src/capabilities/authoring/api/catalog.ts

`POST /api/v1/orgs/{org_slug}/programmes`Add Programme
Now: web/src/capabilities/authoring/api/catalog.ts, web/src/domains/assess/NewSitting.tsx, web/src/domains/assess/api.ts

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

`POST /api/v1/orgs/{org_slug}/station-templates`Create Station Template
Now: web/src/capabilities/authoring/api/templates.ts, web/src/capabilities/authoring/templates/paths.ts, web/src/domains/assess/dashboard/support.ts

`POST /api/v1/orgs/{org_slug}/station-templates/{template_id}/copy`Copy Station Template
Now: web/src/capabilities/authoring/api/templates.ts

`POST /api/v1/orgs/{org_slug}/station-templates/{template_id}/publish`Publish Station Template
Now: web/src/capabilities/authoring/api/templates.ts

`POST /api/v1/orgs/{org_slug}/station-templates/{template_id}/versions`Add Station Template Version
Now: web/src/capabilities/authoring/api/templates.ts

`POST /api/v1/orgs/{org_slug}/station-templates/{template_id}/versions/{version}/archive`Archive Station Template Version
Now: web/src/capabilities/authoring/api/templates.ts

`POST /api/v1/orgs/{org_slug}/stations/{station_id}/versions`Add Version
Now: web/src/capabilities/authoring/api/stations.ts, web/src/capabilities/authoring/sections/StationVersionHistory.tsx, web/src/capabilities/stations/api.ts

`POST /api/v1/orgs/{org_slug}/stations/{station_id}/versions/{version}/archive`Archive Version
Now: web/src/capabilities/authoring/api/stations.ts

`POST /api/v1/orgs/{org_slug}/stations/{station_id}/versions/{version}/photos`Add Station Photos
Now: web/src/capabilities/authoring/api/stations.ts

`POST /api/v1/orgs/{org_slug}/stations/{station_id}/versions/{version}/photos/remove`Remove Station Photo
Now: web/src/capabilities/authoring/api/stations.ts

`POST /api/v1/orgs/{org_slug}/stations/{station_id}/versions/{version}/publish`Publish Version
Now: web/src/capabilities/authoring/api/stations.ts

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.

## Tab 1: Exams

[ ] Drafts only

[Adopt from OSCE Guide](AdoptExam.dc.html) [Create exam](NewExam.dc.html)

Exams 3

Final MB OSCE
finals · 2 min reading · 10 min station

(● Published(Ready to schedule[Edit] [Retire]

Year 4 mock
y4-mock · 2 min reading · 8 min station

(● Draft(Needs a marking scheme[Edit] [Publish] [Delete]

SCA
sca · 3 min reading · 12 min station · OSCE Guide

(● Published[Edit]

The "Ready to schedule" / "Needs a marking scheme" / "Not available" chip is new: it joins the exam, its marking scheme and its programme into one status.

## Tab 2: Stations

Published station cases for sessions and practice.
14 stations · 3 templates available

[Import from PDF or Word](ImportStation.dc.html) [New station](NewStation.dc.html)

‹select:
All exams |

finals |
›

‹select:
Active |

Archived |

All |
›
‹input: Search stations by name…›

Station nameExamStatusUsed byCreated atActions

[Breaking bad news](StationBuilder.dc.html) (FINALS(● Published(ApprovedUsed by 312/10/2026, 09:14[Archive] [Open versions ›](StationBuilder.dc.html)

[Chest pain history](StationBuilder.dc.html) (FINALS(● Published(Awaiting approvalNot used30/10/2026, 16:02[Archive] [Open versions ›](StationBuilder.dc.html)

[Abdominal examination](StationBuilder.dc.html) (FINALS(● DraftNot used-[Open versions ›](StationBuilder.dc.html)

[Load more]

"Approved" / "Awaiting approval" is set by OSCE Guide staff; an organisation admin only sees the pill.

## Tab 3: Marking schemes

The marking structure a station is assessed against.
[+ Create marking scheme](SchemeVersions.dc.html)

‹select:
All exams |

finals |
›
‹input: Search marking schemes…›

Marking schemes 3

Consultation skills
(● Live · v2 (Draft · v3

[Open versions ›](SchemeVersions.dc.html)

Final MB global rating
(● Not live (Draft · v1

[Open versions ›](SchemeVersions.dc.html)

SCA domains
(OSCE Guide (● Live · v4

[Open versions ›](SchemeVersions.dc.html)

[Load more marking schemes]

## Tab 4: Station layouts

Define layout and fields for clinical stations. Saved drafts and published versions appear below, but not the starting layouts on the new-template wizard.

[Import from PDF or Word](ImportStation.dc.html) [Create station template](LayoutBuilder.dc.html)

‹select:
All exams |
›
‹input: Search templates…›

Station templates 4

[Communication station](LayoutBuilder.dc.html)
(FINALS (● Live · v2 (Draft · v3

[New draft] [Edit draft](LayoutBuilder.dc.html) [Publish draft] [Archive live] [Delete draft]

[History and examination](LayoutBuilder.dc.html)
(FINALS (● Live · v2

[New draft] [Archive live]

[Untitled template](LayoutBuilder.dc.html)
(Y4-MOCK (● Not live (Draft · v1

[Edit draft](LayoutBuilder.dc.html) [Publish draft] [Delete draft]

[Simulation scenario (ASPiH)](LayoutBuilder.dc.html)
(SCA · Platform template (● Live · v1

[Copy to my organisation]

[Load more templates]

An OSCE Guide template offers only "Copy to my organisation" and opens read only. Clicking a title opens its live version read only.

## Tab 5: Programmes

A programme groups this institution's sittings under one exam.

[Exams the platform publishes](AdoptExam.dc.html) [New programme]

Programmes 3

🎓 Final MB OSCE
finals · own

(● Active[Retire]

🎓 Year 4 mock
y4-mock · own

(● Draft[Activate]

🎓 SCA
sca · adopted · OSCE Guide exam

(● Retired[Reactivate]

In the redesign the exam's "Available for scheduling" switch drives these same three actions; this list stays for anyone who wants it.

## Tab 6: Empty and read-only states

## No exams yet

Create an exam, attach a marking scheme version, then publish it to run sittings against it.

## No draft exams

Everything here is published. Clear the filter to see the whole catalogue.

## No stations yet

Create one with New station, from a template or straight from a prompt.

## No matching stations

Try a different name, or clear the exam filter.

## No marking schemes

Create a marking scheme, publish a version, then build exams and templates on it.

## No saved templates yet

The layouts on New template are starting points only. They are not added here until you finish the wizard (Save draft), then Publish from this list.

## No programmes yet

Add a programme for each exam you run sittings against.

Supervisor (no authoring rights)

Lists show with no create or write buttons. Empty lists read "Nothing here yet."

Could not load more rubrics: network error [Dismiss]

Could not load stations. [Retry]

## Dialog: editexam

## Edit exam

Publishing is refused without a marking scheme version.
[Open the full form ›](ExamSettings.dc.html)
[Cancel]

## Dialog: retire

## Retire "Final MB OSCE"?

It stops being offered for new practice and sittings, and cannot be published again. What was already attempted against it stays as it is.

[Cancel] [Retire exam]

## Dialog: delexam

## Delete "Year 4 mock"?

Only a draft nothing was ever built on can be deleted this way. Anything with a station, a sitting or an attempt against it cannot be deleted. Retire it instead.

[Cancel] [Delete exam]

## Dialog: archst

## Archive "Breaking bad news" (v2)?

v2: Used 3 times: by circuits, attempts, peer sessions and practice sets. Past attempts stay intact. The station is removed from the live library.

[Cancel] [Archive]

## Dialog: archlive

## Archive live v2?

Stations already built on it keep that shape; nothing new may bind to it.

[Cancel] [Archive live]

## Dialog: deldraft

## Delete draft?

Draft v3 will be removed permanently. Live v2 stays published.

[Cancel] [Delete draft]

## Dialog: delonly

## Delete "Untitled template"?

This removes the template entirely.

[Cancel] [Delete draft]

## Dialog: addprog

## Add programme

Choose the exam. Sittings you schedule for it are grouped under this programme.

Exam

‹select:
Select an exam… |

Final MB OSCE (finals) |
›

Only published exams are listed.

[Cancel] [Add programme]
