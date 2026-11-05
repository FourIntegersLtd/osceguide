# Settings

Source: `boards/Settings.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Organisation | 2. Single sign-on | 3. Provisioning | 4. Your account | 5. Preferences | 6. Invoices

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

Settings

# Settings

Your organisation, how people sign in, and your own account.

[{{ t.label }}]
Same tabs as today, reordered so an admin sees the organisation first (today's default tab is already Organisation). Leaving with an unsaved name asks "Leave without saving? You have unsaved changes. If you leave now they will be lost." (Leave / Stay). Supervisors see only Your account and Preferences. New: Invoices.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/settings`

Who sees it
Org admin (Organisation, SSO, Provisioning); everyone (Your account, Preferences)

Owner agent
`access-owner` · prove with `verify-access` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/settings/OrgSettings.tsx`

- `web/src/domains/assess/settings/ScimTokens.tsx`

- `web/src/domains/assess/settings/ssoStatus.ts`

API calls (all exist; add no endpoint, change no schema)

`DELETE /api/v1/orgs/{org_slug}/scim/tokens/{token_id}`Revoke Scim Token
Now: web/src/domains/assess/api.ts

`GET /api/v1/auth/sso/sign-in`Read Sign In
Now: capabilities/account/api.ts

`GET /api/v1/sso/saml/{connection_id}/metadata`Saml Metadata
No screen calls this today.

`GET /api/v1/orgs/{org_slug}`Read Organization
Now: web/src/app/(auth)/accept-invitation/page.tsx, web/src/app/(auth)/auth/sso/callback/page.tsx, web/src/app/(auth)/change-password/page.tsx

`GET /api/v1/orgs/{org_slug}/audit`List Audit
Now: web/src/domains/assess/team/api.ts, web/src/domains/platform/Overview.tsx, web/src/domains/platform/api.ts

`GET /api/v1/orgs/{org_slug}/scim/tokens`List Scim Tokens
Now: web/src/domains/assess/api.ts

`GET /api/v1/orgs/{org_slug}/sso-status`Read Status
Now: web/src/domains/assess/api.ts

`PATCH /api/v1/orgs/{org_slug}`Update Organization Details
Now: web/src/app/(auth)/accept-invitation/page.tsx, web/src/app/(auth)/auth/sso/callback/page.tsx, web/src/app/(auth)/change-password/page.tsx

`PATCH /api/v1/orgs/{org_slug}/mfa-policy`Set Staff Mfa Policy
Now: web/src/domains/platform/api.ts

`POST /api/v1/auth/sso/callback`Sso Callback
Now: capabilities/account/api.ts

`POST /api/v1/auth/sso/login`Sso Login
Now: capabilities/account/api.ts

`POST /api/v1/sso/saml/{connection_id}/acs`Saml Acs
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/scim/tokens`Issue Scim Token
Now: web/src/domains/assess/api.ts

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.

## Tab 1: Organisation

## Organisation

The web address is fixed. Contact support to change it.

Name
‹input: St Mary's Medical School›

Web address
‹input: /stmarys›
[Save name]

## Tab 2: Single sign-on

## Single sign-on

OSCE Guide sets this up with you. Contact support to change it.

People sign in with an email and password.(● Not connected

It is set up but switched off, so passwords are used.(● Switched off

Everyone signs in with “Microsoft Entra ID”. Passwords are not accepted.(● Connected

The three states above are alternatives; one shows.

## Two-step sign-in for staff

Staff sign in with a password alone.(Not required

Staff must confirm a code as well as a password.(Required

## Tab 3: Provisioning

## Provisioning

Let your identity provider add and remove people here. Give each connector its own token.

Copy this token now; it cannot be shown again. `scim_9f2c…e81a` [Dismiss]

‹input: Connector name›[Create token]

Entra ID
scim_9f2c… · last used 4 Nov
[Revoke]

Okta trial
scim_11ab… · never used
(Revoked

Empty: "No tokens yet."

## Tab 4: Your account

## Account

Your sign-in details and account actions

DO

[Change photo]
JPG or PNG, 5 MB max

Username
‹input: dr.okafor›

Email
‹input: okafor@stmarys.ac.uk›

[Change password] [Update profile]

## Two-factor sign-in

Ask for a code from your authenticator app at every sign-in

Add a code from an authenticator app when you sign in.[Set up]

✓ Enabled You sign in with your password and a code from your authenticator app. 8 recovery codes left.
Your organisation requires two-factor sign-in for its staff.
[New recovery codes] [Turn off]

Off and on are alternatives; one shows. Turn off is hidden when two-factor is required.

## Organisations

They see your sittings, marks, released results and practice on their stations.

▣ St Mary's Medical SchoolOwner

## Your data

A copy of everything we hold about you.
[Download as PDF]

## Delete your account

You are signed out straight away. You have 30 days to reopen it.
[Delete account]

## Tab 5: Preferences

## Preferences

Accessibility and notifications.

◷ Extra reading time
Your timers: 04:00 reading, 14:00 consultation
[Edit] On

When off: "Give yourself longer than the exam allows to read the doctor information and to consult. Your own timers replace the exam's in practice stations". If a change fails: "Your change was not saved. Try again".

## Tab 6: Invoices

## Invoices

Invoices OSCE Guide raises for St Mary's, and the purchase order number your finance team needs on them.
[Open invoices](Invoices.dc.html) (New

## Dialog: pw

## Update password

Choose a new password for your account

Password details

Current Password
‹input: ›

New Password
‹input: ›
At least 12 characters, mixing letters with numbers, punctuation or capitals.

Confirm New Password
‹input: ›

That's not your current password.

[Cancel] [Update password]

On success: "Password updated. This device stays signed in; your other devices are signed out within 15 minutes."

## Dialog: tfa

## Set up two-factor sign-in

After setup, every sign-in needs your password and a 6-digit code from your authenticator app.

- Open an authenticator app such as Google Authenticator, Microsoft Authenticator or 1Password and scan this code.

Setting up on the phone that has the authenticator app? Tap Open in your authenticator app instead of scanning.

- Or add an account by hand with this setup key: `JBSW Y3DP EHPK 3PXP`

- Enter the six-digit code the app shows.

Code from your app
‹input: ›

[Cancel] [Turn on two-factor sign-in]

## Dialog: codes

## Your recovery codes

Keep these somewhere safe. Each one signs you in once if you lose your authenticator. This is the only time we will show them.

8KQ2-7HXM3PLD-9WZAQ7NB-2RFEM4TC-8YJKV1SX-6GDHZ9WE-4UPL

[Copy] [Download]

[ ] I have saved my recovery codes

[Done]

## Dialog: newcodes

## New recovery codes

Your current recovery codes stop working as soon as new ones are made.

Code from your authenticator app
‹input: ›

[Cancel] [Make new codes]

## Dialog: tfaoff

## Turn off two-factor sign-in?

You will sign in with your password alone. Your recovery codes stop working. Enter a code from your authenticator app to continue.

Code from your authenticator app
‹input: ›

[Cancel] [Turn off]

## Dialog: del1

## Delete your account?

Here is what happens.

- Now: you are signed out, paid access ends with the account, and there is no refund.

- For 30 days: sign in again to reopen the account.

- After 30 days: your details, attempts and feedback are erased.

Type DELETE to confirm
‹input: ›

Password (leave blank if you sign in through your organisation)
‹input: ›

[Keep account] [Continue]

## Dialog: del2

## Delete your account?

This cannot be undone after 30 days.

[Cancel] [Delete my account]

## Dialog: timers

## Extra reading time

Set your own timers for practice stations. They replace the exam's default times while this is on.

Reading timer (doctor information)
‹input: 04:00›

Simulation timer (consultation)
‹input: 14:00›

[Cancel] [Use these timers]
