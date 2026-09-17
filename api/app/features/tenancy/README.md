# tenancy

## Purpose
Which organisation a resource belongs to, and what a person may do inside it. Owns
`organizations`, `memberships` and the `audit_log`, and the policy predicates every
org-scoped slice depends on.

This is the one place that decides whether a caller may act. b2c had no orgs at all
(admin was three hardcoded emails); b2b had the right shape but enforced it with
per-handler checks and a `find_slot_by_id_global` that bypassed org scoping entirely.

## Use cases
- As an **org admin**, I invite a member, assign a role and revoke or restore access.
- As a **member of two organisations**, I switch workspace so that I act in the right one.
- As **anyone**, I see which organisations I belong to and what I may do in each.
- As a **platform admin**, I provision an institution or a partner organisation.
- As a **platform admin**, I suspend an organisation so that nobody can sign in to it.
- As an **org admin**, I read the audit log of who changed what.

## Aggregates & invariants
**Organization** is the aggregate root; memberships and audit entries belong to it.

- `slug` is the URL identifier and is unique; `id` is the foreign key everywhere else.
  A slug is resolved to an id once per request and never stored as a foreign key.
- A user may hold memberships in many organisations, at most one per `(org, role)`.
- The **active workspace** must be an organisation the principal is a member of.
  Switching to any other is `forbidden` (403), never a silent no-op.
- `platform_admin` is **not** an org admin and inherits no org role. Ported verbatim
  from `b2b policy.py:27-28`, which is the current behaviour and is correct.
- Org admin is `owner | admin | institution_admin | partner_admin`.
  Institution admin — who alone signs off candidate results — is the narrower
  `owner | admin | institution_admin`.
- A suspended or inactive organisation refuses login for its members; only `trial`
  and `active` permit access.
- Every org-scoped repository method in every slice takes `org_id` first. Guard-enforced.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/auth/switch-workspace` | bearer | re-issues the token; `forbidden` (403) if not a member |
| GET | `/api/v1/orgs/{org_slug}` | org member | |
| GET | `/api/v1/orgs/{org_slug}/memberships` | org admin | cursor-paginated |
| POST | `/api/v1/orgs/{org_slug}/memberships` | org admin | `membership_exists` (409) |
| PATCH | `/api/v1/orgs/{org_slug}/memberships/{id}` | org admin | role change |
| POST | `/api/v1/orgs/{org_slug}/memberships/{id}/revoke` | org admin | |
| POST | `/api/v1/orgs/{org_slug}/memberships/{id}/restore` | org admin | |
| GET | `/api/v1/orgs/{org_slug}/audit` | org admin | cursor-paginated |
| GET | `/api/v1/me/capabilities` | bearer | read model; replaces the browser's copy of this policy |
| POST | `/api/v1/platform/organizations` | platform admin | institution or partner |
| POST | `/api/v1/platform/organizations/{slug}/suspend` | platform admin | |
| GET | `/api/v1/platform/organizations` | platform admin | every tenant; `?status=` |
| PATCH | `/api/v1/platform/organizations/{slug}` | platform admin | name, type, contract dates — never the slug |
| POST | `/api/v1/platform/organizations/{slug}/restore` | platform admin | lifts a suspension |
| GET | `/api/v1/platform/users` | platform admin | `?q=` part of an email |
| PUT | `/api/v1/platform/users/{id}/platform-admin` | platform admin | grant or revoke the console |
| GET | `/api/v1/platform/overview` | platform admin | counts, not lists |

The console **cannot delete an organisation**, and that is a decision rather
than an omission: its rows include candidate results, which exist to be
defensible months later, and a cascade would take them. Suspension is the
reversible mechanism and it now has an inverse.

## Jobs
None yet. Membership invitation email is enqueued through `notifications`.

## Cross-slice dependencies
Calls `identity` service to read and create users. Nothing calls into this slice
except through its service.
