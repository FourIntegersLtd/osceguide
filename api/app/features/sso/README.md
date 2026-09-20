# sso

## Purpose

Which organisation a visitor belongs to, before they have proved anything.

The retiring client answered this in the browser bundle:

```js
const PARTNER_SSO_HOSTS = ["bmj.osceguide.com"];
```

— a hostname allow-list shipped to every visitor, with the tenant slug, the
button's wording and the "no password form here" rule compiled in beside it.
Adding a partner meant a frontend deploy, and the four facts could drift apart
from each other and from the backend. This slice makes it a server-side fact.

## Aggregates & invariants

`OrganizationSso` is the aggregate: one row per organisation, holding the
provider, the issuer, the flags and the button's wording. `OrganizationSsoBinding`
rows hang off it — the hosts and email domains that resolve to that
organisation.

- **A binding belongs to exactly one organisation.** Unique on `(kind, value)`
  across the whole platform, not within an organisation: two rows claiming
  `nhs.net` would make home-realm discovery a coin toss.
- **`sso_only` requires `enabled`.** Restricting sign-in to SSO while SSO is off
  leaves nobody a way in. Refused by the service and by a check constraint,
  because a settings row is exactly the kind of thing edited by hand at three in
  the morning.
- **`enabled` requires an issuer.** Turning it on with nothing to turn it on
  against is a configuration that cannot work.
- **A binding is stored as it will arrive.** Hosts and domains are lower-cased
  and stripped of scheme, path and port, so a pasted URL still matches a `Host:`
  header.
- **Saving replaces the binding set.** The screen sends the whole list; a merge
  would make removing a hostname impossible.

## Routes

| Route | Who |
|---|---|
| `GET /auth/sso/sign-in?host=…` or `?email=…` | **Anyone, unauthenticated** — it is what a sign-in page asks before anybody has signed in. A 404 means "sign in here, with a password", which is the ordinary case. |
| `GET /platform/orgs/{slug}/sso` | Platform admin |
| `PUT /platform/orgs/{slug}/sso` | Platform admin |

The write is platform-admin deliberately. Whoever controls the issuer controls
who may sign in as that institution's members, so it is not a field to put on a
customer's own settings screen beside their logo. When there is an onboarding
flow with a domain verification step in it, that is where this moves.

## Jobs

None.

## Cross-slice dependencies

`tenancy`, through its service only: `org_ref_by_slug` to resolve the URL and
`org_ref_by_id` to name the organisation on the sign-in page. This slice never
reads the `organizations` table.

## What is deliberately not here

The sign-in itself. `/auth/sso/login` and `/auth/sso/callback` do not exist,
because who verifies the identity is an open decision: the retiring backend
brokered through Clerk to Microsoft, and direct OIDC to Entra is the other
candidate. `Provider` names both so a stored row says what it expects, and
nothing here implies a flow has been built.

Until that lands **`sso_only` is a display rule, not an enforcement one** — the
page hides its password form, and nothing in this slice refuses a password
login. See `docs/port-gaps.md`.
