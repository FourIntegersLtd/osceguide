# New station form

Source: `boards/CreateStation.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Manual | 2. Generate with AI | 3. No template (by exam) | 4. Before a template is chosen

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

[‹ New station](NewStation.dc.html)

Exams › Stations

# New station

Choose a published template and fill in content manually or with AI. Saving opens the draft so you can publish it.

[{{ t.label }}]
Same as today's New station screen. "Generate with AI" appears only once a published template is chosen. What changed: it is reached from the New station chooser (previous board), with the exam already picked.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/authoring/stations/new`

Who sees it
author_content

Owner agent
`content-owner` · prove with `verify-content` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/capabilities/authoring/stations/CreateStationScreen.tsx`

- `web/src/capabilities/authoring/stations/GeneratedDraft.tsx`

- `web/src/capabilities/authoring/hooks/useCreateStationForm.ts`

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

## Tab 1: Manual

▸ Station details

Station title
‹input: e.g. Chest pain counselling›

Template

‹select:
No template: write it from a prompt |

*Communication station (v2) |
›

Only published templates can be used for stations. A station with no template is still a real station. It just borrows the exam's own shape rather than a reusable one.

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

[Cancel](Exams.dc.html) [Save draft](StationBuilder.dc.html)

## Tab 2: Generate with AI

▸ Station details

Station title
‹input: e.g. Chest pain counselling›

Template

‹select:
No template: write it from a prompt |

*Communication station (v2) |
›

Only published templates can be used for stations. A station with no template is still a real station. It just borrows the exam's own shape rather than a reusable one.

▸ Generate draft

Paste a short prompt (a few lines). We'll auto-fill the template fields below; you can edit anything afterward.

‹textarea: e.g. 72F falls at home, hip pain, shortened externally rotated leg. Candidate to assess and plan management including peri-op considerations.›
[Generate draft]

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

[Cancel](Exams.dc.html) [Save draft](StationBuilder.dc.html)

## Tab 3: No template (by exam)

▸ Station details

Station title
‹input: e.g. Chest pain counselling›

Template

‹select:
*No template: write it from a prompt |

Communication station (v2) |
›

Only published templates can be used for stations. A station with no template is still a real station. It just borrows the exam's own shape rather than a reusable one.

Exam

‹select:
Select an exam… |

*Final MB OSCE |
›

Station type

‹select:
Choose the kind of station… |
›

These stations are scored differently, so the prompt is steered by the type rather than left to guess.

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

[Cancel](Exams.dc.html) [Save draft](StationBuilder.dc.html)

## Tab 4: Before a template is chosen

No published templates yet. You can still write a station by choosing its exam below. Choose a published template to generate a draft with AI.

## Choose a template or an exam

The full station form appears here as soon as you pick a published template, or say which exam this station is for.

## This exam needs a template

This exam has no built-in station layout. Create a station template for this exam here. It is published when you save it, and you come straight back to this station.
[Create a station template](LayoutBuilder.dc.html)

## Generated draft

Read this before you publish. It is not live until you save.
