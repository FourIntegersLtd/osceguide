# Add people

Source: `boards/AddPeople.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Trainee: one person | 2. Trainees: spreadsheet | 3. Staff: invite | 4. Staff: spreadsheet

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

[‹ People](People.dc.html)

Organise

# Add people

Add the trainees who will sit your exams or training sessions, or invite staff to run and mark them.

[{{ t.label }}]
One page for both kinds of person (today: People › Add people and Team › Add people). Supervisors see "Only an owner or admin can add trainees. Ask one of them to add the people you need on the roster." Next: the person gets an email (Accept invitation, row 4).

▸ Build spec: how to build this screen

Route
`sheet opened from People`

Who sees it
manage_roster / manage_team

Owner agent
`institution-owner` · prove with `verify-institution` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/roster/AddTraineePanel.tsx`

- `web/src/domains/assess/roster/BulkImportDialog.tsx`

- `web/src/domains/assess/roster/csv.ts`

- `web/src/domains/assess/team/InvitePanel.tsx`

- `web/src/domains/assess/team/BulkInviteDialog.tsx`

API calls (all exist; add no endpoint, change no schema)

`GET /api/v1/orgs/{org_slug}/memberships`List Memberships
Now: web/src/domains/assess/api.ts, web/src/domains/assess/team/api.ts, web/src/domains/platform/api.ts

`PATCH /api/v1/orgs/{org_slug}/memberships/{membership_id}`Change Membership Role
Now: web/src/domains/assess/api.ts, web/src/domains/assess/team/api.ts, web/src/domains/platform/api.ts

`POST /api/v1/orgs/{org_slug}/memberships`Add Membership
Now: web/src/domains/assess/api.ts, web/src/domains/assess/team/api.ts, web/src/domains/platform/api.ts

`POST /api/v1/orgs/{org_slug}/memberships/bulk`Add Memberships
Now: web/src/domains/assess/team/api.ts

`POST /api/v1/orgs/{org_slug}/memberships/bulk/resend-invitation`Bulk Resend Membership Invitations
Now: web/src/domains/assess/team/api.ts

`POST /api/v1/orgs/{org_slug}/memberships/{membership_id}/resend-invitation`Resend Membership Invitation
Now: web/src/domains/assess/team/api.ts

`POST /api/v1/orgs/{org_slug}/memberships/{membership_id}/restore`Restore Membership
Now: web/src/domains/assess/team/api.ts

`POST /api/v1/orgs/{org_slug}/memberships/{membership_id}/revoke`Revoke Membership
Now: web/src/domains/assess/team/api.ts

`POST /api/v1/orgs/{org_slug}/roster/resolve`Resolve Roster
Now: web/src/domains/assess/roster/api.ts

`POST /api/v1/orgs/{org_slug}/trainees`Add Trainee
Now: web/src/domains/assess/api.ts, web/src/domains/assess/dashboard/OrgDashboard.tsx, web/src/domains/assess/dashboard/support.ts

`POST /api/v1/orgs/{org_slug}/trainees/bulk`Add Trainees
Now: web/src/domains/assess/roster/api.ts

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.

## Tab 1: Trainee: one person

## Add one person

They are invited by email. If they have no account yet, we create one and send them a link to choose a password. If that email cannot reach them, set a temporary password to relay by hand.

Full name
‹input: e.g. Amina Khan›

Email address
‹input: amina@hospital.nhs.uk›

Year group (optional)

‹select:
No year group |

June 2026 intake |
›

An intake, such as "June 2026". Year groups are created under People › Groups and year groups.

[x] Set a temporary password instead of emailing a link

Temporary password

‹input: tide-maple-42-orbit›[Generate]

At least 12 characters, mixing letters with numbers, punctuation or capitals. Only used if they have no account yet; they must change it when they first sign in.

[+ Add trainee]

amina@hospital.nhs.uk is on the roster.

Password for amina@hospital.nhs.uk
tide-maple-42-orbit
Tell them privately. They must change it when they first sign in. It is not shown again once you dismiss this.
[Copy] [Done](People.dc.html)

amina@hospital.nhs.uk is already on this roster.

## Import a spreadsheet

Upload a list of trainees saved from Excel or Google Sheets as a .csv file. Anyone already on the list is skipped and shown to you.
[Import from spreadsheet]

## Tab 2: Trainees: spreadsheet

## Import trainees

One spreadsheet of trainees, saved as .csv. The first row must name the columns.

Required column
`email` Their email address

Optional columns
`firstName`, `lastName`, or one `name`; `cohort` or `group`: a year group that already exists here (e.g. "June 2026")

Example
`email,firstName,lastName,cohortamina@hospital.nhs.uk,Amina,Khan,June 2026`

⇧

Drop your .csv here, or choose a file

.csv files only

trainees-year5.csv · 3.2 KB

48 rows ready to import.

Line 14: not a valid email address, so that row is left out.Line 22: the address already appears earlier in the file, so it is counted once.

No year group here is called Year 6, Foundation.
[x] Create those year groups when importing

Otherwise those people are added with no year group.

[Cancel] [Import 48 trainees]

46 added, 2 skipped.

Not imported

ben@stmarys.ac.uk: already on the roster

amara@: not a usable email address

[Done](People.dc.html)

## Tab 3: Staff: invite

## Invite someone to the team

Supervisors run circuits and mark them. Admins also manage the team and sign off results.

Email address
‹input: supervisor@hospital.nhs.uk›
If they have no account yet we create one and email them a link to choose a password.

Their role

‹select:
Supervisor |

Admin |
›

Runs circuits and marks the candidates on them.

[ ] Set a temporary password instead of emailing a link

Temporary password

‹input: tide-maple-42-orbit›[Generate]

At least 12 characters, mixing letters with numbers, punctuation or capitals. Only used if they have no account yet; they must change it when they first sign in.

[+ Add person]

Invited clarke@stmarys.ac.uk. They have been emailed a link to choose a password.

patel@stmarys.ac.uk already had an account and is now Supervisor here.

## Import a spreadsheet

Upload a list of staff saved from Excel or Google Sheets as a .csv file. Anyone already on the team is skipped and shown to you.
[Import from spreadsheet]

## Tab 4: Staff: spreadsheet

## Import staff

One spreadsheet of supervisors and admins, saved as .csv. The first row must name the columns.

Required columns
`email` Their email address; `role` Either `supervisor` or `admin`

Example
`email,rolesupervisor@hospital.nhs.uk,supervisoradmin@hospital.nhs.uk,admin`

⇧

Drop your .csv here, or choose a file

.csv files only

6 rows ready to import.

Line 4 named a role this organisation cannot give. Only supervisor or admin can be invited, so those rows are left out.

[Cancel] [Invite 5 people]

5 added, 1 skipped. 5 people were emailed a link to choose a password. They cannot sign in until they use it.

Not imported

patel@stmarys.ac.uk: already on the team with that role
