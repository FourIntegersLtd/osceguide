# People

Source: `boards/People.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Trainees | 2. Staff | 3. Groups and year groups | 4. Exam access | 5. History | 6. Empty and error states

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

Organise

# People

Everyone in St Mary's. Trainees sit sittings; staff (supervisors and admins) run circuits and mark them.

[Add people](AddPeople.dc.html)

[{{ t.label }}]
What changed: the Team page is now the Staff tab here (/team still opens it). "Move to group…" is now "Move to year group…", with a separate "Add to group…". New: staff bulk revoke; Exam access now has a screen.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/trainees (and /team, which must keep working)`

Who sees it
manage_roster (trainees), manage_team (staff)

Owner agent
`institution-owner` · prove with `verify-institution` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/PeopleTabs.tsx`

- `web/src/domains/assess/roster/Roster.tsx`

- `web/src/domains/assess/roster/TraineesPanel.tsx`

- `web/src/domains/assess/roster/TraineeRowActions.tsx`

- `web/src/domains/assess/roster/TraineeBulkBar.tsx`

- `web/src/domains/assess/roster/CohortsPanel.tsx`

- `web/src/domains/assess/roster/GroupsPanel.tsx`

- `web/src/domains/assess/roster/AccessPanel.tsx`

- `web/src/domains/assess/team/MembersPanel.tsx`

- `web/src/domains/assess/team/ActivityPanel.tsx`

API calls (all exist; add no endpoint, change no schema)

`DELETE /api/v1/orgs/{org_slug}/cohorts/{cohort_id}`Remove Cohort
Now: web/src/domains/assess/roster/api.ts

`DELETE /api/v1/orgs/{org_slug}/trainee-groups/{group_id}`Remove Group
Now: web/src/domains/assess/roster/api.ts

`DELETE /api/v1/orgs/{org_slug}/trainees/{trainee_id}`Delete Trainee
Now: web/src/domains/assess/api.ts, web/src/domains/assess/dashboard/OrgDashboard.tsx, web/src/domains/assess/dashboard/support.ts

`GET /api/v1/orgs/{org_slug}/audit`List Audit
Now: web/src/domains/assess/team/api.ts, web/src/domains/platform/Overview.tsx, web/src/domains/platform/api.ts

`GET /api/v1/orgs/{org_slug}/cohorts`List Cohorts
Now: web/src/domains/assess/roster/api.ts

`GET /api/v1/orgs/{org_slug}/entitlements`List Org Entitlements
Now: web/src/capabilities/account/access.ts, web/src/capabilities/account/api.ts, web/src/capabilities/account/settings/PaymentsPanel.tsx

`GET /api/v1/orgs/{org_slug}/memberships`List Memberships
Now: web/src/domains/assess/api.ts, web/src/domains/assess/team/api.ts, web/src/domains/platform/api.ts

`GET /api/v1/orgs/{org_slug}/practice-access`List Practice Access
No screen calls this today.

`GET /api/v1/orgs/{org_slug}/trainee-groups`List Groups
Now: web/src/domains/assess/roster/api.ts

`GET /api/v1/orgs/{org_slug}/trainee-groups/{group_id}/members`List Group Members
Now: web/src/domains/assess/roster/api.ts

`GET /api/v1/orgs/{org_slug}/trainees`List Trainees
Now: web/src/domains/assess/api.ts, web/src/domains/assess/dashboard/OrgDashboard.tsx, web/src/domains/assess/dashboard/support.ts

`PATCH /api/v1/orgs/{org_slug}/cohorts/{cohort_id}`Edit Cohort
Now: web/src/domains/assess/roster/api.ts

`PATCH /api/v1/orgs/{org_slug}/memberships/{membership_id}`Change Membership Role
Now: web/src/domains/assess/api.ts, web/src/domains/assess/team/api.ts, web/src/domains/platform/api.ts

`PATCH /api/v1/orgs/{org_slug}/trainee-groups/{group_id}`Rename Group
Now: web/src/domains/assess/roster/api.ts

`PATCH /api/v1/orgs/{org_slug}/trainees/{trainee_id}`Edit Trainee
Now: web/src/domains/assess/api.ts, web/src/domains/assess/dashboard/OrgDashboard.tsx, web/src/domains/assess/dashboard/support.ts

`POST /api/v1/orgs/{org_slug}/circuits/{circuit_id}/append-trainees`Append Trainees
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/cohorts`Add Cohort
Now: web/src/domains/assess/roster/api.ts

`POST /api/v1/orgs/{org_slug}/entitlements`Grant Org Entitlement
Now: web/src/capabilities/account/access.ts, web/src/capabilities/account/api.ts, web/src/capabilities/account/settings/PaymentsPanel.tsx

`POST /api/v1/orgs/{org_slug}/entitlements/{entitlement_id}/revoke`Revoke Org Entitlement
Now: web/src/domains/assess/roster/api.ts

`POST /api/v1/orgs/{org_slug}/memberships`Add Membership
Now: web/src/domains/assess/api.ts, web/src/domains/assess/team/api.ts, web/src/domains/platform/api.ts

`POST /api/v1/orgs/{org_slug}/memberships/bulk`Add Memberships
Now: web/src/domains/assess/team/api.ts

`POST /api/v1/orgs/{org_slug}/memberships/bulk/resend-invitation`Bulk Resend Membership Invitations
Now: web/src/domains/assess/team/api.ts

`POST /api/v1/orgs/{org_slug}/memberships/bulk/revoke`Bulk Revoke Memberships
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/memberships/{membership_id}/resend-invitation`Resend Membership Invitation
Now: web/src/domains/assess/team/api.ts

`POST /api/v1/orgs/{org_slug}/memberships/{membership_id}/restore`Restore Membership
Now: web/src/domains/assess/team/api.ts

`POST /api/v1/orgs/{org_slug}/memberships/{membership_id}/revoke`Revoke Membership
Now: web/src/domains/assess/team/api.ts

`POST /api/v1/orgs/{org_slug}/practice-access`Grant Practice Access
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/practice-access/bulk`Grant Practice Access In Bulk
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/practice-access/{access_id}/revoke`Revoke Practice Access
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/trainee-groups`Add Group
Now: web/src/domains/assess/roster/api.ts

`POST /api/v1/orgs/{org_slug}/trainees/bulk/cohort`Bulk Set Trainee Cohort
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/trainees/bulk/resend-invitation`Bulk Resend Trainee Invitations
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/trainees/bulk/revoke`Bulk Revoke Trainees
No screen calls this today.

`POST /api/v1/orgs/{org_slug}/trainees/{trainee_id}/access`Set Access
Now: web/src/domains/assess/roster/api.ts

`POST /api/v1/orgs/{org_slug}/trainees/{trainee_id}/anonymise`Anonymise Trainee
Now: web/src/domains/assess/roster/api.ts

`POST /api/v1/orgs/{org_slug}/trainees/{trainee_id}/resend-invitation`Resend Invitation
Now: web/src/domains/assess/roster/api.ts

`PUT /api/v1/orgs/{org_slug}/trainee-groups/{group_id}/members`Set Group Members
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

## Tab 1: Trainees

## 48 trainees across 3 programmes

212 stations sat so far.

Emailed chloe@stmarys.ac.uk a link to choose a password for St Mary's Medical School.

48 trainees‹input: Search trainees…›[Invite everyone not signed in on this page (2)]

[ ] Select all on this page
2 selected[Resend invitations]

‹select:
Move to year group… |

No year group |

Year 5 |

Year 4 |
›

‹select:
Add to group… |

Tuesday rotation |
›

[Revoke access] [Clear]

SelectNameYear groupProgrammeSatStatus

[ ]
A

Amara Okoye

amara@stmarys.ac.uk

Year 5Final-year OSCE6(● Member
[Edit] [Resend invitation] [Revoke] [Delete] [Anonymise]

[ ]
B

Ben Hart

ben@stmarys.ac.uk

Year 5Final-year OSCE4(● Booked
[Edit] [Revoke] [Delete] [Anonymise]

[ ]
C

Chloe Imran

chloe@stmarys.ac.uk

Year 5Final-year OSCE0(● Invited, not accepted
[Edit] [Resend invitation] [Revoke] [Delete] [Anonymise]

[ ]
D

Dev Shah

dev@stmarys.ac.uk

No groupNo programme0(● Added, no account yet
[Edit] [Send invitation] [Revoke] [Delete] [Anonymise]

[ ]
E

Esme Lowe

esme@stmarys.ac.uk

Year 4Year 4 mock3(● Access revoked
[Edit] [Restore] [Delete] [Anonymise]

[Load more]

Looking for supervisors and admins? They are on the Staff tab.

## Tab 2: Staff

Patel@stmarys.ac.uk is now Supervisor.

4 staff accounts‹input: Search staff…›[Resend invitations (1)]

1 selected[Resend invitation] [Revoke access] [Clear] (New

EmailRoleCircuits ledAccessActions

[ ] okafor@stmarys.ac.uk Owner0(● Active
[Revoke]

[ ] patel@stmarys.ac.uk Supervisor4(● Active
[Change role] [Revoke]

[ ] clarke@stmarys.ac.uk (InvitedSupervisor2(● Active
[Resend invitation] [Change role] [Revoke]

[ ] reid@stmarys.ac.uk Admin0(● Revoked
[Change role] [Restore]

## Tab 3: Groups and year groups

## Year groups (cohorts)

An intake, such as a start date. Each trainee can be in one year group, chosen when they are added.

June 2026 intake
2026/27
[Rename] [Delete]

Year 4
2026/27
[Rename] [Delete]

▸ Create a year group

‹input: e.g. June 2026 intake›‹input: 2026/27›[Create year group]

Empty: "No year groups yet. Create one below, or leave people without."

## Groups

A named list of people you can add to a circuit together, such as a rotation team or a resit group. A person can be in more than one.

Tuesday rotation
8 people
[People] [Rename] [Delete]

▸ Create a group

Everyone in your organisation sees the same group names.
‹input: e.g. Tuesday rotation›[Create group]

Empty: "No groups yet. Create one below and choose who is in it."

## Tab 4: Exam access

## Grant exam access

Lets trainees practise between sittings. They do not need it to take an exam they are booked on.

Who

‹select:
Choose a trainee… |

Ben Hart |
›

Exam

‹select:
Choose… |

FY-OSCE |
›

Until (optional)
‹input: ›

[Grant access]

ben@stmarys.ac.uk can now practise FY-OSCE.

‹input: Search by person or exam…›

WhoExamStatusFromUntilActions

ben@stmarys.ac.ukFY-OSCE(Live1 NovNo end date[Revoke]

amara@stmarys.ac.ukY4-MOCK(Expired1 Sep31 Oct

Not on this rosterFY-OSCE(Revoked2 OctNo end date

Empty: "No practice access given yet. Trainees can still take every exam they are booked on." · Search with no match: "No grants match."

## Tab 5: History

Done by
‹input: name@hospital.nhs.uk›

Action
‹input: e.g. membership.›

[Filter] [Clear]

Invited clarke@stmarys.ac.uk as supervisor
By okafor@stmarys.ac.uk
5 Nov, 08:12

Changed patel@stmarys.ac.uk's role to supervisor
By okafor@stmarys.ac.uk
3 Nov, 16:40

Moved 12 trainees to Year 5
By okafor@stmarys.ac.uk
2 Nov, 10:05

Filtered with no match: "Nothing matches those filters. Try a different address or action." · Nothing yet: "Invitations, role changes and roster edits appear here as they happen."

## Tab 6: Empty and error states

## No trainees yet

Add trainees so you can put them on an exam or training circuit.
[Add people](AddPeople.dc.html)

## No staff yet

Invite a supervisor so somebody can run a circuit.
[Invite staff](AddPeople.dc.html)

Search with no match

No trainees match “zz”.

Could not load trainees. [Retry]

Supervisor (read only)

Contact an owner or admin to change who has access.

Dev Shah has a decision recorded and cannot be deleted. Revoke their access instead.

Dev Shah’s name and email address have been removed. Any results already recorded are kept.

## Dialog: edit

## Edit trainee

Only what is on this form is written. The email address cannot be changed here, because it keeps this person’s results linked to them.

Member
‹input: chloe@stmarys.ac.uk›

First name
‹input: Chloe›

Last name
‹input: Imran›

Year group

‹select:
No year group |

*Year 5 |
›

An intake. Choose an existing one; year groups are created under Groups and year groups.

[Cancel] [Save]

## Dialog: revoke

## Revoke access

Chloe Imran will not be able to sign in or sit anything, and stays on the roster with their results intact.

[Cancel] [Revoke access]

## Dialog: restore

## Restore access

Esme Lowe will be able to sign in and sit again.

[Cancel] [Restore access]

## Dialog: delete

## Delete Dev Shah?

You can only delete a trainee with no results recorded. If they have been examined, remove their access instead.

[Cancel] [Delete]

## Dialog: anon

## Anonymise Dev Shah?

Dev Shah's name and email address will be scrubbed and their access revoked. Any decision already recorded about them is kept. This cannot be undone.

[Cancel] [Anonymise]

## Dialog: bulkrevoke

## Revoke access for 2 people?

They will not be able to sign in or sit anything, and stay on the roster with their results intact.

[Cancel] [Revoke access]

## Dialog: role

## Change role

patel@stmarys.ac.uk's role in this organisation.

Their role

‹select:
Supervisor |

Admin |
›

Supervisor: runs circuits and marks the candidates on them. Admin: also manages the team and the organisation's settings, and signs off results.

[Cancel] [Save role]

## Dialog: srevoke

## Revoke access

patel@stmarys.ac.uk will lose access to this organisation. Nothing they have marked is deleted.

[Cancel] [Revoke access]

## Dialog: srestore

## Restore access

reid@stmarys.ac.uk will be able to sign in to this organisation again, with the role they had.

[Cancel] [Restore access]

## Dialog: sbulk

## Revoke access for 1 staff member?

They lose access to this organisation. Nothing they have marked is deleted. The owner and the last admin are skipped.

[Cancel] [Revoke access]

## Dialog: rcohort

## Rename year group

Everyone in this intake stays in it. Only the name changes.

New name
‹input: June 2026 intake›

Academic year
‹input: 2026/27›
Leave blank to take the year off this intake.

[Cancel] [Save]

## Dialog: dcohort

## Delete year group

Delete “Year 4”? Nobody can be put into it afterwards. This cannot be undone, and a year group that still has trainees in it is not deleted. The 2 sittings held for it are kept but no longer belong to any year group.

[Cancel] [Delete year group]

## Dialog: rgroup

## Rename group

Everyone still in “Tuesday rotation” stays in it. Only the name changes.

New name
‹input: Tuesday rotation›

[Cancel] [Rename]

## Dialog: dgroup

## Delete group?

Delete “Tuesday rotation”? It still has 8 people in it, and a group is not deleted while it does. Empty it from People first.

[Cancel] [Delete group]

## Dialog: members

## People in Tuesday rotation

Tick everyone who belongs to this group. Saving replaces the current list.

8 of 48 selected.

[x] Amara Okoyeamara@stmarys.ac.uk

[x] Ben Hartben@stmarys.ac.uk

[ ] Chloe Imranchloe@stmarys.ac.uk

[Cancel] [Save group]
