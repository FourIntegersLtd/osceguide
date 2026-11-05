# Station builder

Source: `boards/StationBuilder.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Draft, ready | 2. Draft, unsaved | 3. Published | 4. Archived and errors

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

[‹ Stations](Exams.dc.html)

[{{ t.label }}]
Same as today's station detail. Trial mark lives on the marking scheme, not here. Fact check and approval are OSCE Guide staff tools, so a school never sees them.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/authoring/stations (station row opens it)`

Who sees it
author_content

Owner agent
`content-owner` · prove with `verify-content` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/capabilities/authoring/sections/StationDetail.tsx`

- `web/src/capabilities/authoring/sections/BriefEditor.tsx`

- `web/src/capabilities/authoring/sections/StationInstanceContentPanel.tsx`

- `web/src/capabilities/authoring/sections/StationVersionHistory.tsx`

- `web/src/capabilities/authoring/sections/StationUsedBy.tsx`

API calls (all exist; add no endpoint, change no schema)

`DELETE /api/v1/orgs/{org_slug}/stations/{station_id}/versions/{version}`Delete Version
Now: web/src/capabilities/authoring/api/stations.ts, web/src/capabilities/authoring/sections/StationVersionHistory.tsx, web/src/capabilities/stations/api.ts

`GET /api/v1/station-generation-profiles`List Station Generation Profiles
Now: capabilities/authoring/structure/b2b/lib/api/stationGenerationProfiles.ts

`GET /api/v1/station-generation-profiles/{profile_key}`Get Station Generation Profile
Now: web/src/capabilities/authoring/structure/b2b/lib/api/stationGenerationProfiles.ts

`GET /api/v1/stations/{station_id}/comments`List Station Comments
Now: web/src/capabilities/community/api.ts

`GET /api/v1/stations/{station_id}/versions`Station Version History
Now: web/src/capabilities/authoring/api/stations.ts, web/src/capabilities/authoring/sections/StationVersionHistory.tsx, web/src/capabilities/stations/api.ts

`GET /api/v1/orgs/{org_slug}/station-imports`List Station Imports
Now: web/src/capabilities/authoring/api/imports.ts

`GET /api/v1/orgs/{org_slug}/station-imports/{import_id}`Read Station Import
Now: web/src/capabilities/authoring/api/imports.ts

`GET /api/v1/orgs/{org_slug}/stations`List Stations
Now: web/src/app/app/[workspace]/authoring/stations/new/page.tsx, web/src/app/app/[workspace]/stations/page.tsx, web/src/app/staff/authoring/page.tsx

`PATCH /api/v1/orgs/{org_slug}/stations/{station_id}/versions/{version}`Edit Version
Now: web/src/capabilities/authoring/api/stations.ts, web/src/capabilities/authoring/sections/StationVersionHistory.tsx, web/src/capabilities/stations/api.ts

`PATCH /api/v1/orgs/{org_slug}/stations/{station_id}/versions/{version}/brief`Edit Brief
Now: web/src/capabilities/authoring/api/stations.ts

`POST /api/v1/stations/{station_id}/comments`Comment On Station
Now: web/src/capabilities/community/api.ts

`POST /api/v1/orgs/{org_slug}/station-imports`Upload Station Import
Now: web/src/capabilities/authoring/api/imports.ts

`POST /api/v1/orgs/{org_slug}/station-imports/{import_id}/station`Draft Station From Import
Now: web/src/capabilities/authoring/api/imports.ts

`POST /api/v1/orgs/{org_slug}/stations/autogenerate-draft`Autogenerate Station Draft
Now: web/src/capabilities/authoring/api/scope.ts, web/src/capabilities/authoring/api/stations.ts

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

## Tab 1: Draft, ready

‹input: Breaking bad news›
finals · version 3

(● Draft[Delete draft]

DraftWritten

PublishNot published

Ready. Publishing makes this version the one candidates are assessed against.[Publish](ExamDetail.dc.html)

▸ Station content

Version 3. Edit the sections below; Save in the bar above stores them.

▸ 1. Candidate brief

Notes the candidate reads before starting the station.

‹textarea: ›

▸ 2. Patient script

The script the simulated patient follows.

‹textarea: ›

▸ 3. Examiner notes

Model answers and marking notes.

‹textarea: ›

▸ 4. Faculty notes

Setup, debrief and teaching notes.

‹textarea: ›

Photos

Upload photos
Click to upload or drag and drop

‹input: https://… (image, audio, video or PDF)›‹input: Caption (optional)›[Add]

## Reading brief

What the candidate reads before the station starts. Saving this does not cut a new version.

‹textarea: ›
[Save brief]

## Publish

Publishing makes v3 the version candidates are assessed against. A published version is what an attempt was marked against, so it is archived rather than deleted.

This station has no candidate brief, so candidates see nothing during reading time. You can still publish.
[Publish anyway]

▸ Revision history

v3
(● Draft Never published

v2
(● Published Published 12 Oct · Used by 3

v1
(● Archived Archived 12 Oct · Not used anywhere yet

One version only: "No revisions listed. This station has one version, and it is the one above."

## Tab 2: Draft, unsaved

‹input: Breaking bad news›
finals · version 3

(● Draft[Delete draft]

DraftWritten

PublishNot published

Unsaved changes. Fill all required fields.[Save]

Leaving now asks "Leave without saving? You have unsaved changes. If you leave now they will be lost." (Stay / Leave).

▸ Station content

Version 3. Edit the sections below; Save in the bar above stores them.

▸ 1. Candidate brief

Notes the candidate reads before starting the station.

‹textarea: ›

▸ 2. Patient script

The script the simulated patient follows.

‹textarea: ›

▸ 3. Examiner notes

Model answers and marking notes.

‹textarea: ›

▸ 4. Faculty notes

Setup, debrief and teaching notes.

‹textarea: ›

Photos

Upload photos
Click to upload or drag and drop

‹input: https://… (image, audio, video or PDF)›‹input: Caption (optional)›[Add]

## Tab 3: Published

‹input: Breaking bad news›
finals · version 3

(● Published[New draft version] [Archive]

DraftWritten

PublishLive

Published and live. Its details are below, read only. Start a new draft version to change it.[New draft version]

▸ Station content

Version 3. Published, so it is read only. Create a new draft version to edit. Photos stay editable.

▸ 1. Candidate brief

Notes the candidate reads before starting the station.

‹textarea: ›

▸ 2. Patient script

The script the simulated patient follows.

‹textarea: ›

▸ 3. Examiner notes

Model answers and marking notes.

‹textarea: ›

▸ 4. Faculty notes

Setup, debrief and teaching notes.

‹textarea: ›

Photos

Upload photos
Click to upload or drag and drop

‹input: https://… (image, audio, video or PDF)›‹input: Caption (optional)›[Add]

## Reading brief

What the candidate reads before the station starts. Saving this does not cut a new version.

‹textarea: ›
[Save brief]

▸ Revision history

v3
(● Draft Never published

v2
(● Published Published 12 Oct · Used by 3

v1
(● Archived Archived 12 Oct · Not used anywhere yet

One version only: "No revisions listed. This station has one version, and it is the one above."

## Tab 4: Archived and errors

‹input: Breaking bad news›
finals · version 3

(● Archived[New draft from this]

DraftWritten

PublishArchived

Archived. Past attempts keep it; start a new draft version to edit.[New draft version]

▸ Revision history

v3
(● Draft Never published

v2
(● Published Published 12 Oct · Used by 3

v1
(● Archived Archived 12 Oct · Not used anywhere yet

One version only: "No revisions listed. This station has one version, and it is the one above."

Template structure is not available in the catalogue. Reload templates or edit from the template list.

No layout is defined for exam finals. Create a station template for this exam first. [Create a station template](LayoutBuilder.dc.html)

## Dialog: del

## Delete draft v3 of "Breaking bad news"?

v3: Not used anywhere yet. The draft is removed. Published versions are untouched. If this is the station's only version, the station is deleted with it.

[Cancel] [Delete]

## Dialog: arch

## Archive v2 of "Breaking bad news"?

v2: Used 3 times: by circuits, attempts, peer sessions and practice sets. Past attempts stay intact. If an older version is still published, the station stays in the live library on that one; otherwise it is retired from the live library.

[Cancel] [Archive]
