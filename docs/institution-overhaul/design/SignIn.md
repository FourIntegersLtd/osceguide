# Sign in

Source: `boards/SignIn.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Sign in | 2. After sign-in steps | 3. Forgot password | 4. Refusals and SSO

## Always on screen (menu, header, notes, build spec)

OG
OSCE Guide

[{{ t.label }}]

What changed: a first sign-in lands on Home's setup assistant.

▸ Build spec: how to build this screen

Route
`/sign-in`

Who sees it
Anyone

Owner agent
`access-owner` · prove with `verify-access` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/capabilities/account/api.ts`

- `web/src/foundation/platform-client/auth.ts`

API calls (all exist; add no endpoint, change no schema)

`GET /api/v1/auth/sso/sign-in`Read Sign In
Now: capabilities/account/api.ts

`POST /api/v1/auth/password-reset`Begin Password Reset
Now: foundation/platform-client/auth.ts

`POST /api/v1/auth/password-reset/confirm`Confirm Password Reset
Now: foundation/platform-client/auth.ts

`POST /api/v1/auth/sso/callback`Sso Callback
Now: capabilities/account/api.ts

`POST /api/v1/auth/sso/login`Sso Login
Now: capabilities/account/api.ts

`POST /api/v1/auth/login`Login

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.

## Tab 1: Sign in

# Sign in

Email
‹input: okafor@stmarys.ac.uk›

Password
‹input: ••••••••••›

[Sign in](Main.dc.html) [Sign in with your organisation (single sign-on)]

[Forgot your password?] · New organisation? [Register](RegisterOrg.dc.html) · Help: support@osceguide.co.uk

If your organisation requires single sign-on: "Your organisation signs you in through its own system. Use the single sign-on button."

## Tab 2: After sign-in steps

# Two-step sign-in

Enter the 6-digit code from your authenticator app, or a recovery code.
‹input: 123 456›[Continue](Main.dc.html)

## Choose a new password

You signed in with a temporary password. Choose your own before you carry on.
‹input: New password›‹input: Confirm it›[Save password](Main.dc.html)

## Signing you in

Single sign-on callback. Errors explain themselves, for example "Your organisation has not set up single sign-on for this email."

## Tab 3: Forgot password

# Reset your password

We email you a link if an account uses this address.
‹input: Email›[Send the link]

## Choose a new password

Opened from the email link.
‹input: New password›‹input: Confirm it›[Reset password](SignIn.dc.html)

## Tab 4: Refusals and SSO

This organisation signs in with its own sign-in. Use the button above.

That email or password is not right.

## Single sign-on

Signing you in…

Your sign-in provider refused this sign-in. Try again or ask your administrator.
