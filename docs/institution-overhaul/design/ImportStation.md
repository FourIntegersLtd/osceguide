# Import a station

Source: `boards/ImportStation.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Into a layout you have | 2. Make a new layout from a file | 3. Refusals

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

Exams › Stations

# Import from PDF or Word

Upload a station you have already written. We copy its words into a template. Nothing is added or rewritten.

[{{ t.label }}]
Today a dialog on the Stations and Station layouts tabs; drawn full size so every state shows. Nothing about it changes.

▸ Build spec: how to build this screen

Route
`dialog on Stations and Station layouts tabs`

Who sees it
author_content

Owner agent
`content-owner` · prove with `verify-content` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/capabilities/authoring/imports/ImportStationDialog.tsx`

- `web/src/capabilities/authoring/imports/importCopy.ts`

- `web/src/capabilities/authoring/api/imports.ts`

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

## Tab 1: Into a layout you have

Exam

‹select:
Final MB OSCE |
›

Template

‹select:
Simulation scenario (ASPiH) (standard) |

Communication station |

Make a new template from this file |
›

⇧

Drop your station files, or click to choose

PDF or Word (.docx), one station per file, up to 10MB each. You can add several files at once.

bad-news.docx, abdo-exam.pdf

[Cancel](Exams.dc.html) [Upload 2 files]

Recent imports

chest-pain.pdf
Reading the file and drafting a template. This takes about a minute.

(…

bad-news.docx
Template drafted. Review it; creating the station also publishes the template.Check these against your file, the wording may differ: Examiner notes

[Review the template](LayoutBuilder.dc.html) [Publish template and create the station]

abdo-exam.pdf
Draft station created. It is in your Stations list.Every part of the template was filled word for word from your file.

[Open](StationBuilder.dc.html)

scan.pdf
Could not be imported

(Failed

## Tab 2: Make a new layout from a file

Template

‹select:
Make a new template from this file |
›

⇧

Drop one station file, or click to choose

PDF or Word (.docx), one station per file, up to 10MB each. Your first file sets the template. After you publish it you can add the rest together.

[Cancel] [Upload]

## Tab 3: Refusals

That file is larger than 10MB.

Only PDF and Word (.docx) files can be imported.

A new template is made from one file. Choose one.

It is not a PDF or Word file we can read, or it has nothing in it.

Too many imports just now. Wait a minute and upload the rest again.

Left empty because your file had nothing for them: Faculty notes
