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
  from `b2b policy.py:27-28`, which is the current behaviour and is correct. The
  exception is the console's own membership routes — seating a member, moving a
  role, revoking and restoring — which go through the same service and leave the
  same audit row, but are reached by `PlatformAdmin` rather than a relaxation of
  `OrgAdmin`. A freshly provisioned organisation has no admin to seat its first
  member; an admin who leaves without naming a successor leaves the same gap.
- Naming somebody who has no account **invites** them: the account is created
  without a password and they are emailed a link to choose one. Refusing with
  `user_not_found` meant every tutor had to register unprompted first.
- **Staff are memberships, not roster entries.** `roster` owns the people an
  organisation examines; the people who examine them live here, because a
  membership is what decides what a signed-in person may do. That is why the
  bulk add the retiring client called "import staff from a spreadsheet" is
  `POST /memberships/bulk` rather than a `roster` route — and why no temporary
  password appears in it: an unknown address is invited, exactly as it is one at
  a time. The exception is the single add: the platform console's seat route, an
  org admin's team invite and the roster's single add take an optional
  `temporary_password` because the invitation email cannot always be delivered.
  It applies only to a brand-new account (never an existing one;
  `temporary_password_applied` says which), which must change it at first
  sign-in, and the audit row says "(temporary password)". While the account is
  still `must_change_password`, `POST /platform/users/{id}/temporary-password`
  re-issues a lost one. A platform admin cannot revoke their own console access.
- Org admin is `owner | admin | institution_admin | partner_admin`.
  Institution admin — who alone signs off candidate results — is the narrower
  `owner | admin | institution_admin`.
- An organisation always keeps an administrator: revoking or demoting the last
  active org admin is refused `last_admin` (409), on the org and staff routes and
  for a bulk revoke (refused whole). The browser does not count admins.
- A suspended or inactive organisation refuses login for its members; only `trial`
  and `active` permit access.
- Every org-scoped repository method in every slice takes `org_id` first. Guard-enforced.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/auth/switch-workspace` | bearer | re-issues the token; `forbidden` (403) if not a member |
| GET | `/api/v1/orgs/{org_slug}` | org member | |
| PATCH | `/api/v1/orgs/{org_slug}` | org admin | rename only (B-33); slug, type and contract stay with platform staff |
| GET | `/api/v1/orgs/{org_slug}/memberships` | org admin | cursor-paginated |
| POST | `/api/v1/orgs/{org_slug}/memberships` | org admin | `membership_exists` (409); an unknown address is **invited** (`invited: true`) with no display name until they set one, so nothing greets them by email (B39) |
| POST | `/api/v1/orgs/{org_slug}/memberships/bulk` | org admin | up to 500 rows; a person already holding the role is reported in `skipped`, never fatal. Each row is the single act above it |
| PATCH | `/api/v1/orgs/{org_slug}/memberships/{id}` | org admin | role change; `last_admin` (409) |
| POST | `/api/v1/orgs/{org_slug}/memberships/{id}/revoke` | org admin | `last_admin` (409) |
| POST | `/api/v1/orgs/{org_slug}/memberships/{id}/restore` | org admin | |
| GET | `/api/v1/orgs/{org_slug}/audit` | org admin | cursor-paginated |
| GET | `/api/v1/me/capabilities` | bearer | read model; replaces the browser's copy of this policy. `schedule_sittings` is org admin only, the same guard as creating a sitting (B39) |
| POST | `/api/v1/platform/organizations` | platform admin | institution or partner |
| POST | `/api/v1/platform/organizations/{slug}/memberships` | platform admin | seats a member — usually the first owner, or the successor an admin left without naming; the same service and audit row as the org's own route |
| PATCH | `/api/v1/platform/organizations/{slug}/memberships/{id}` | platform admin | role change, for support |
| POST | `/api/v1/platform/organizations/{slug}/memberships/{id}/revoke` | platform admin | `last_admin` (409) |
| POST | `/api/v1/platform/organizations/{slug}/memberships/{id}/restore` | platform admin | the admin who locked themselves out |
| POST | `/api/v1/platform/organizations/{slug}/contract` | platform admin | new dates and, unless `restore: false`, the suspension lifted with them; audited `organization.contract_renewed`; an end date not in the future is 422 `contract_end_in_past` |
| POST | `/api/v1/platform/organizations/{slug}/suspend` | platform admin | |
| GET | `/api/v1/platform/organizations` | platform admin | every tenant; `?status=` |
| PATCH | `/api/v1/platform/organizations/{slug}` | platform admin | name, type, contract dates — never the slug; a start after the end (the stored other date counts) is 422 `contract_dates_out_of_order`, here and on the renewal |
| POST | `/api/v1/platform/organizations/{slug}/restore` | platform admin | lifts a suspension; a lapsed `contract_ends_at` is cleared with it so the hourly sweep does not re-suspend |
| GET | `/api/v1/platform/organizations/{slug}/memberships` | platform admin | read-only member list, for support |
| GET | `/api/v1/platform/organizations/{slug}/audit` | platform admin | one organisation's audit log, for support |
| GET | `/api/v1/platform/users` | platform admin | `?q=` part of an email; `?platform_admin=true` only console users |
| GET | `/api/v1/platform/users/{id}` | platform admin | flags, `status`, last sign-in, `exam_code`, `exam_date`, `extra_reading_percent`, memberships. The directory the console lists is `GET /platform/directory` (`dashboard`) |
| PATCH | `/api/v1/platform/users/{id}` | platform admin | `name`, `exam_code`, `status` (`active`/`deactivated`), `exam_date`, `extra_reading_percent` (0–100); audited |
| POST | `/api/v1/platform/users/{id}/reset-password` | platform admin | sends the reset link; audited |
| PUT | `/api/v1/platform/users/{id}/platform-admin` | platform admin | grant or revoke the console; audited |
| GET | `/api/v1/platform/admins` | platform admin | everyone who may use the console |
| POST | `/api/v1/platform/admins` | platform admin | grant the console by email; unknown addresses are **invited** (`invited: true`) |
| GET | `/api/v1/platform/audit` | platform admin | every organisation's log and the platform's own rows; `?org_slug=`, `?actor_email=`, `?action=` (prefix) |
| GET | `/api/v1/platform/users/{id}/audit` | platform admin | what was done to the account and what it did |
| GET | `/api/v1/platform/overview` | platform admin | counts by status, and the one list: `at_risk` — suspended, lapsed, or ending within thirty days |

The console **cannot delete an organisation**, and that is a decision rather
than an omission: its rows include candidate results, which exist to be
defensible months later, and a cascade would take them. Suspension is the
reversible mechanism and it now has an inverse.

## Jobs
`suspend_lapsed_organizations` — hourly. Suspends every `trial`/`active`
organisation whose `contract_ends_at` has passed and writes an
`organization.contract_lapsed` audit row. Renewal is the existing `PATCH` of
the end date plus `restore`. Contract dates were recorded and enforced by
nothing before this.

The invitation email is queued through `identity.service_invitations`, in the
transaction that creates the membership.

## Cross-slice dependencies
Calls `identity` service to read and create users. Nothing calls into this slice
except through its service.
