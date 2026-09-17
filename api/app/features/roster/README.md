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
  org), and exists before they have ever signed in. `user_id` is filled from
  either end: rostering somebody who already has an account links them, and
  registering claims every roster entry waiting for that address (bound into
  `identity.register` by `main.py`, since `identity` sits below this slice).
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
| POST | `/api/v1/orgs/{org_slug}/trainees` | org admin | `trainee_exists` (409) |
| POST | `/api/v1/orgs/{org_slug}/trainees/{id}/access` | org admin | one route for revoke and restore |
| GET/POST | `/api/v1/orgs/{org_slug}/cohorts` | member / admin | |
| GET/POST | `/api/v1/orgs/{org_slug}/trainee-groups` | member / admin | `group_exists` (409) |
| PUT | `/api/v1/orgs/{org_slug}/trainee-groups/{id}/members` | org admin | states the whole membership |
| POST | `/api/v1/orgs/{org_slug}/roster/resolve` | org member | preview, changes nothing |

## Jobs
Spreadsheet upload and invitation email are not yet ported.

## Cross-slice dependencies
`sittings` asks this slice whether the people a circuit names may be rostered
onto one (R3): revoking access stops somebody signing in, and now also stops
them being scheduled into an examination they could not attend.

None outward. `sittings` will call this to resolve a circuit's roster.
