# New station

Source: `boards/NewStation.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

## Always on screen (menu, header, notes, build spec)

# New station
[Cancel](ExamDetail.dc.html)

For exam

‹select:
Final-year OSCE |

Year 4 mock |

UKMLA CPSA practice |
›

Only exams that are ready show here. A station can only go into sittings of its own exam.

How do you want to start?

[{{ w.title }}{{ w.body }}]

What happens next

{{ cur.next }}

[{{ cur.cta }}](StationBuilder.dc.html)

▸ Build spec: how to build this screen

Route
`/app/[workspace]/authoring/stations/new (chooser)`

Who sees it
author_content

Owner agent
`content-owner` · prove with `verify-content` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/capabilities/authoring/stations/CreateStationScreen.tsx`

- `web/src/capabilities/authoring/parts/useCreateStationChoices.ts`

API calls (all exist; add no endpoint, change no schema)

`GET /api/v1/orgs/{org_slug}/station-imports`List Station Imports
Now: web/src/capabilities/authoring/api/imports.ts

`GET /api/v1/orgs/{org_slug}/station-imports/{import_id}`Read Station Import
Now: web/src/capabilities/authoring/api/imports.ts

`POST /api/v1/orgs/{org_slug}/station-imports`Upload Station Import
Now: web/src/capabilities/authoring/api/imports.ts

`POST /api/v1/orgs/{org_slug}/station-imports/{import_id}/station`Draft Station From Import
Now: web/src/capabilities/authoring/api/imports.ts

`POST /api/v1/orgs/{org_slug}/stations`Create Station
Now: web/src/app/app/[workspace]/authoring/stations/new/page.tsx, web/src/app/app/[workspace]/stations/page.tsx, web/src/app/staff/authoring/page.tsx

`POST /api/v1/orgs/{org_slug}/stations/autogenerate-draft`Autogenerate Station Draft
Now: web/src/capabilities/authoring/api/scope.ts, web/src/capabilities/authoring/api/stations.ts

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.
