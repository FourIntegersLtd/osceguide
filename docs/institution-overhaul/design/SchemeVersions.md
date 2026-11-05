# Marking scheme versions

Source: `boards/SchemeVersions.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Versions | 2. New marking scheme

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

[‹ Marking schemes](Exams.dc.html)

[{{ t.label }}]
Same as today's scheme detail and "New marking scheme" screens. The builder itself is the next board.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/authoring/rubrics, /authoring/rubrics/new`

Who sees it
author_content

Owner agent
`marking-owner` · prove with `verify-marking` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/capabilities/authoring/sections/RubricDetail.tsx`

- `web/src/capabilities/authoring/rubrics/RubricStartScreen.tsx`

- `web/src/capabilities/authoring/sections/versions.ts`

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

## Tab 1: Versions

Marking scheme

# Consultation skills

Each version is a frozen copy. Candidates are marked against the live one.

[New draft version]

Version 3
You are an experienced GP examiner. Mark the consultation against…

(● Draft[Edit in the builder](MarkingScheme.dc.html) [Publish]

Version 2
You are an experienced GP examiner. Mark the consultation…

(● Published[Open in the builder](MarkingScheme.dc.html) [Archive]

Version 1
No system prompt.

(● Archived[Open in the builder](MarkingScheme.dc.html)

With no versions: "This marking scheme has no versions yet. Cut a draft to start writing it." An OSCE Guide scheme shows "Copy to my marking schemes" instead of publish and archive.

## Tab 2: New marking scheme

Marking schemes

# New marking scheme

Start blank or from a published marking scheme. You get a draft to edit; nothing is used until you publish it.

Title
‹input: Copy of SCA domains›
Set here; a marking scheme keeps its title across versions.

‹input: Search published marking schemes…›
Start from

( ) (Blank
Blank

(•) (OSCE Guide v4
SCA domains

Red / Amber / Green · 12 competencies

Data gathering · Clinical management · Relating to others

( ) (Yours v2
Consultation skills

Named scale · 8 competencies

[Cancel](Exams.dc.html) [Copy and edit](MarkingScheme.dc.html)

## Dialog: arch

## Archive this version?

Version 2 stops being used to mark new attempts. If it is the current version, the newest other published version takes over. It is refused while an exam or an upcoming sitting still uses it.

[Cancel] [Yes, archive]
