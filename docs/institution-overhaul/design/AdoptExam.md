# Adopt an exam

Source: `boards/AdoptExam.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

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

Organise

# Programmes

A programme is an exam you run sittings against. Adopt one the platform publishes or add your own, activate it, and it is offered when you schedule a sitting.

SCA is now one of your programmes. Schedule a sitting against it whenever you are ready.

Exams the platform publishes

SCA
sca · 120 library stations

(Adopted

PLAB 2
plab2 · 64 library stations

[Adopt]

Orthopaedics
ortho · 38 library stations

[Adopting…]

Your programmes

Programmes 2

🎓 Final MB OSCE
finals · own

(● Active[Retire]

🎓 SCA
sca · adopted · OSCE Guide exam

(● Active[Retire]

Same as today's /programmes page. The catalogue section is hidden when OSCE Guide publishes nothing. What changed: it is reached from Exams › Adopt from OSCE Guide and from step 1 of Home.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/programmes`

Who sees it
Org admin

Owner agent
`institution-owner` · prove with `verify-institution` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/programmes/Programmes.tsx`

- `web/src/domains/assess/programmes/PlatformExams.tsx`

- `web/src/domains/assess/programmes/api.ts`

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
