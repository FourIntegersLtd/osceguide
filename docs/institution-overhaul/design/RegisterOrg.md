# Register your organisation

Source: `boards/RegisterOrg.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Form | 2. Sent

## Always on screen (menu, header, notes, build spec)

OG
OSCE Guide

[{{ t.label }}]
Same as today: a request (POST /site/messages), not instant creation. Fixed: the old copy promised purposes "later in Settings", which does not exist.

▸ Build spec: how to build this screen

Route
`/organisations/new`

Who sees it
Anyone signed in

Owner agent
`institution-owner` · prove with `verify-institution` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/NewOrganisation.tsx`

- `web/src/domains/assess/newOrganisationRequest.ts`

API calls (all exist; add no endpoint, change no schema)

`POST /api/v1/auth/register`Register
Now: foundation/platform-client/auth.ts

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.

## Tab 1: Form

# Register your organisation

Tell us who you are. We set your organisation up and email you a link to sign in, usually within a working day.

Organisation name
‹input: St Mary's Medical School›

Type

‹select:
Medical school |

Training programme |

Deanery |

Employer |
›

Employer sets you up for hiring: candidates and assessments instead of trainees and sittings.

What you will use it for

Mock OSCEsFormal examsSelf practiceRecruitment

You can tell us more when we contact you.

Your name
‹input: ›

Work email
‹input: ›

Anything else (optional)

‹textarea: ›

[Request set-up]

Already set up? [Sign in](SignIn.dc.html)

## Tab 2: Sent

# Request received

We will email you at the address you gave once your organisation is ready. Then sign in and the setup assistant takes you through it, step by step.
[Go to sign in](SignIn.dc.html)
