# roster

## Purpose
Who an organisation teaches: trainees, the cohorts they belong to, and the
groups a circuit can be built from.

## Use cases
- As an **org admin**, I add trainees and put them in a cohort.
- As an **org admin**, I make a group and say who is in it.
- As an **org admin**, I revoke someone's access and restore it later.
- As a **supervisor**, I see who would be on a circuit before I build it.

## Aggregates & invariants
**Trainee**, **Cohort** and **TraineeGroup** are each org-owned roots;
**TraineeGroupMember** joins the last two.

- A trainee is identified within an organisation by email (`citext`, unique per
  org). `user_id` is always filled: rostering somebody who already has an
  account links them, and rostering somebody who does not **invites** them —
  the account is created and linked in the same call, and they are emailed a
  link to choose a password. A slot names a `users.id`, so a rostered trainee
  with no account could never be scheduled. Registering still claims any row
  left unlinked (as the migration leaves them), bound into `identity.register`
  by `main.py` since `identity` sits below this slice.
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
- A revoked trainee cannot be rostered — otherwise revoking access still leaves
  them sitting next week's examination.
- Resolving a roster keeps order, because a training circuit pairs trainee *i*
  with station *i*. An empty linked group is **reported**, not passed over, so a
  supervisor finds out now rather than when the examination starts.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/orgs/{org_slug}/trainees` | org member | supervisors need names to run a circuit |
| POST | `/api/v1/orgs/{org_slug}/trainees` | org admin | `trainee_exists` (409); an unknown address is invited and linked |
| POST | `/api/v1/orgs/{org_slug}/trainees/bulk` | org admin | up to 500 rows; duplicates reported in `skipped`, never fatal |
| POST | `/api/v1/orgs/{org_slug}/trainees/{id}/access` | org admin | one route for revoke and restore |
| GET/POST | `/api/v1/orgs/{org_slug}/cohorts` | member / admin | |
| GET/POST | `/api/v1/orgs/{org_slug}/trainee-groups` | member / admin | `group_exists` (409) |
| PUT | `/api/v1/orgs/{org_slug}/trainee-groups/{id}/members` | org admin | states the whole membership |
| POST | `/api/v1/orgs/{org_slug}/roster/resolve` | org member | preview, changes nothing |

## Jobs
None. The invitation email is queued through `identity.service_invitations` in
the transaction that creates the roster row; the browser parses the
spreadsheet and posts rows to `/trainees/bulk`.

## Cross-slice dependencies
`sittings` asks this slice whether the people a circuit names may be rostered
onto one (R3): revoking access stops somebody signing in, and now also stops
them being scheduled into an examination they could not attend.

None outward. `sittings` will call this to resolve a circuit's roster.
