# roster

## Purpose
Who an organisation teaches: trainees, the cohorts they belong to, and the
groups a circuit can be built from.

## Use cases
- As an **org admin**, I add trainees and put them in a cohort.
- As an **org admin**, I correct a name or move somebody to another intake.
- As an **org admin**, I rename or remove a group, and rename or retire a cohort.
- As an **org admin**, I send an invitation again when the first one was lost.
- As an **org admin**, I make a group and say who is in it.
- As an **org admin**, I revoke someone's access and restore it later.
- As a **supervisor**, I see who would be on a circuit before I build it.
- As an **org admin**, I read who is in a group, a page at a time.
- As an **org admin**, I issue our identity provider a SCIM token, and revoke it.
- As an **identity provider** (Entra, Okta), I provision the roster over SCIM 2.0:
  users are trainees, groups are trainee groups.

## Aggregates & invariants
**Trainee**, **Cohort** and **TraineeGroup** are each org-owned roots;
**TraineeGroupMember** joins the last two.

- A trainee is identified within an organisation by email (`citext`, unique per
  org). `user_id` is always filled: rostering somebody who already has an
  account links them, and rostering somebody who does not **invites** them —
  the account is created and linked in the same call, and they are emailed a
  link to choose a password. A slot names a `users.id`, so a rostered trainee
  with no account could never be scheduled. Registering still claims any row
  left unlinked (as the migration leaves them), called from `identity`'s
  registration.
  It was filled by nothing at all for the whole build, which left a slot (a
  `users.id`) and a released result (a `trainees.id`) as two unconnected
  records for one person.
- **Group membership is a table.** b2b has none: it matches a trainee's `cohort`
  string against a group's `label`, both lowercased, on every circuit build. So
  renaming a group silently empties it, two groups sharing a label collide, and
  nobody can be in two groups. `app/migration/roster_labels.py` turns that
  matching into rows once, at migration; after that the table is the truth. It
  lives there rather than in this slice's `domain.py` because it is not a rule
  the product enforces — it is how the old shape is read at the moment a tenant
  crosses, and it is deleted with the rest of the migration.
- Setting members replaces them wholesale. The caller is stating who is in the
  group, and a partial update would leave whoever they removed still in it.
- **Renaming a group renames the group.** b2b could not promise that: it matched
  a trainee's `cohort` string against the label, so a rename either emptied the
  group in silence or had to rewrite every one of those strings to match. Here
  the members are rows and the label is a column, so `PATCH /trainee-groups/{id}`
  changes one and leaves the other alone. A rename onto a label another group
  already has is `group_exists` (409) — two spellings of one label are still
  one group.
- **A row that something is still attached to is not deleted.** A group with
  members answers `group_not_empty`, because the membership rows go with it and
  so does anything addressed to it (`core.db.Addressed` points
  `audience_group_id` here with `CASCADE`) — the emptied list is stated first,
  on purpose, through `PUT /trainee-groups/{id}/members`. A cohort with trainees
  in it answers `cohort_in_use`, because `trainees.cohort_id` is `SET NULL`:
  the delete would not fail, it would quietly leave a year group of people
  belonging to nothing, which a screen would then show as a mistake rather than
  report as one. Moving them is `PATCH /trainees/{id}`.
  `sittings.cohort_id` is also `SET NULL`; that column is `sittings`' own, so
  nothing here reads it — see *Cross-slice dependencies*.
- An edit writes only what was sent. `PATCH /trainees/{id}` and
  `PATCH /cohorts/{id}` take `model_fields_set`, the way `PATCH /me` does, so a
  form that posts one corrected field does not clear the others. An explicit
  null *does* clear — that is the edit screen's "No group" option, and the two
  cannot be conflated.
- **An invitation can be sent again; the same link cannot be.** The token is
  stored hashed, which is what makes it worthless to whoever intercepts the
  email including to us, so a re-send mints a fresh one through
  `identity.service_invitations`. Once the person has chosen a password there is
  no invitation left to send and the route answers `invitation_not_pending`
  (409): a set-password link mailed to somebody who can already sign in is a
  way into their account, and `POST /auth/password-reset` is the email they
  actually need.
- A trainee is identified within an organisation by email (`citext`, unique per
  org), and the address is **not editable**: it is what the account link is
  made against, so changing it re-points a person's results rather than fixing
  a typo. The legacy edit screen offered a name and a group and nothing else.
- A revoked trainee cannot be rostered — otherwise revoking access still leaves
  them sitting next week's examination.
- Resolving a roster keeps order, because a training circuit pairs trainee *i*
  with station *i*. An empty linked group is **reported**, not passed over, so a
  supervisor finds out now rather than when the examination starts.
- **SCIM goes through the roster's own use cases** (`service_scim.py`): creating
  a user is `add_trainees` (so the person is invited and linked), `active` is
  `set_access`, names are `update_trainee`, groups are `service_groups`. SCIM
  only translates. Deleting a user **deactivates** them — revoking access keeps
  what was decided about them, as the roster screen does. Deleting a group is
  the provider saying so on purpose, so it is emptied and removed.
- A user's `userName` is their address and cannot change over SCIM
  (`mutability`), for the same reason `PATCH /trainees/{id}` will not change it.
- Attributes the roster does not keep (a title, a department) are ignored, not
  refused: connectors send them unasked. Filters are one `attribute eq "value"`
  clause on `userName`/`emails`/`id` (users) or `displayName`/`id` (groups).
- A SCIM token is stored as a sha256 and shown once. A missing, foreign, revoked
  token and a suspended organisation are one refusal, `scim_unauthorized`.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/orgs/{org_slug}/trainees` | org member | supervisors need names to run a circuit |
| POST | `/api/v1/orgs/{org_slug}/trainees` | org admin | `trainee_exists` (409); an unknown address is invited and linked |
| POST | `/api/v1/orgs/{org_slug}/trainees/bulk` | org admin | up to 500 rows; duplicates reported in `skipped`, never fatal |
| PATCH | `/api/v1/orgs/{org_slug}/trainees/{id}` | org admin | name and intake; only what was sent is written. `trainee_not_found`, `cohort_not_found` (404) |
| POST | `/api/v1/orgs/{org_slug}/trainees/{id}/resend-invitation` | org admin | a **new** set-password link, queued in this transaction; `invitation_not_pending` (409) once they have chosen one |
| POST | `/api/v1/orgs/{org_slug}/trainees/{id}/access` | org admin | one route for revoke and restore |
| GET/POST | `/api/v1/orgs/{org_slug}/cohorts` | member / admin | `cohort_exists` (409) — `(org, name)` is unique |
| PATCH | `/api/v1/orgs/{org_slug}/cohorts/{id}` | org admin | rename, or the academic year; `cohort_not_found` (404), `cohort_exists` (409) |
| DELETE | `/api/v1/orgs/{org_slug}/cohorts/{id}` | org admin | 204; `cohort_in_use` (409) while trainees are on it |
| GET/POST | `/api/v1/orgs/{org_slug}/trainee-groups` | member / admin | `group_exists` (409) |
| PATCH | `/api/v1/orgs/{org_slug}/trainee-groups/{id}` | org admin | rename; the members stay. `group_not_found` (404), `group_exists` (409) |
| DELETE | `/api/v1/orgs/{org_slug}/trainee-groups/{id}` | org admin | 204; `group_not_empty` (409) while it has members |
| PUT | `/api/v1/orgs/{org_slug}/trainee-groups/{id}/members` | org admin | states the whole membership |
| POST | `/api/v1/orgs/{org_slug}/roster/resolve` | org member | preview, changes nothing |
| GET | `/api/v1/orgs/{org_slug}/trainee-groups/{id}/members` | org member | cursor-paged trainees; `group_not_found` (404) |
| POST | `/api/v1/orgs/{org_slug}/scim/tokens` | org admin | 201 with the token, shown once |
| GET | `/api/v1/orgs/{org_slug}/scim/tokens` | org admin | never the token itself |
| DELETE | `/api/v1/orgs/{org_slug}/scim/tokens/{id}` | org admin | 204; refused from the next request |
| GET, POST | `/api/v1/orgs/{org_slug}/scim/v2/Users` | SCIM token | list (`filter`, `startIndex`, `count`) / create |
| GET, PUT, PATCH, DELETE | `/api/v1/orgs/{org_slug}/scim/v2/Users/{id}` | SCIM token | DELETE deactivates |
| GET, POST | `/api/v1/orgs/{org_slug}/scim/v2/Groups` | SCIM token | |
| GET, PUT, PATCH, DELETE | `/api/v1/orgs/{org_slug}/scim/v2/Groups/{id}` | SCIM token | PATCH adds, removes or replaces members |
| GET | `/api/v1/orgs/{org_slug}/scim/v2/ServiceProviderConfig` | SCIM token | |

The write routes live in `router_admin.py` and are mounted by `router.py`,
which is the only thing `main.py` imports from this slice.

## Jobs
The invitation is queued in the transaction that creates a roster row (and, on
a re-send, in the transaction that mints the replacement token). The browser
parses the spreadsheet and posts rows to `/trainees/bulk`.

## Cross-slice dependencies
`sittings` asks this slice whether the people a circuit names may be rostered
onto one (R3): revoking access stops somebody signing in, and now also stops
them being scheduled into an examination they could not attend.

Downward: `identity` for the account behind an address and for both ways of
sending an invitation, `tenancy` for the organisation's name in that
invitation's subject line, and `notifications` for the outbox row itself.

One thing this slice cannot see. `sittings.cohort_id` points at a row owned
here with `SET NULL`, and `sittings` sits **above** `roster` in the layer list,
so `DELETE /cohorts/{id}` can refuse a cohort that still has trainees and has
to let one that only a scheduled sitting names go — quietly detaching it. The
other half of that rule belongs in `sittings`, or on a seam bound in
`main.py`.
