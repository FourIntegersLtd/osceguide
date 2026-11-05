# Accept invitation

Source: `boards/AcceptInvite.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Invitation | 2. Accepted | 3. Problems

## Always on screen (menu, header, notes, build spec)

OG
OSCE Guide

[{{ t.label }}]
What changed: staff land on Home; trainees on My training.

▸ Build spec: how to build this screen

Route
`/invitations/accept (link in the email)`

Who sees it
The invited person

Owner agent
`access-owner` · prove with `verify-access` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/capabilities/account/`

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

## Tab 1: Invitation

# Join St Mary's Medical School

Dr Okafor invited you as a trainee. Choose a password to accept.

Password
‹input: ›

Confirm password
‹input: ›

[Accept invitation]

## Tab 2: Accepted

# You are in

Your sittings appear on your home page once you are booked on one.
[Go to my training](Trainee.dc.html)

## Tab 3: Problems

## This link is incomplete

Open the link from your email again, or ask your administrator to resend it.

## Signed in with a temporary password?

You are asked to "Choose a new password" first (see Sign in).
