# platform-web — AGENTS.md

Read `README.md` first, then
`docs/adr/0001-one-app-shared-capabilities-three-surfaces.md`.

## The one rule

Tiers import downwards only, and lint enforces it:

```
app → surfaces → domains → capabilities → foundation
```

**A capability may not import a domain or a surface.** If a capability needs
something arm-specific, take it as a prop or read it from `useSurface()`. When
that feels wrong, the thing is probably a domain feature with a capability
underneath it — see `domains/assess/OrgDiscussion.tsx`, which is four lines
supplying an org id to a capability that knows nothing about institutions.

## Where things go

| You are adding | It belongs in |
|---|---|
| A screen only consumers see | `domains/train` |
| A screen only institutions see | `domains/assess` |
| Something both could use | `capabilities/<name>` |
| A button, a card, a token | `foundation/ui` |
| An API call | the owning slice's `api.ts` — never inline `fetch` |
| A route | `app/**`, composing the above and holding no logic |

A new capability needs a `capability.ts` declaring its `surfaces`, and an entry
in `capabilities/registry.ts`. Mounting it on an arm is a route file.

## Non-negotiable

- **One HTTP path.** `platformRequest` from `foundation/platform-client`. No
  axios, no bare `fetch` to the API.
- **Branch on `PlatformError.code`, never on `message`.** The old client decided
  whether a trainee retried by matching the words "not live".
- **Authorisation is the server's.** `can(session, "manage_team")` against
  `/me/capabilities`. Never derive a permission from a role in the browser.
- **Permission names are a union** in `foundation/session/permissions.ts`, taken
  from the backend's `tenancy/service.py`. Add one there, not as a literal.
- **Every load goes through `useAsync` + `AsyncBoundary`.** A failure must never
  render as "no data" — that was a finding in the old client's UX audit, 173
  times over.
- **Colours come from tokens.** `bg-canvas`, `text-ink`, `bg-accent`. A literal
  `bg-blue-600` picks one arm's side and breaks the other three skins.
- **The exam clock is the server's.** Read `remaining_seconds` and
  `phase_ends_at`. Never run an authoritative countdown in the browser.
- Strict types. No `any` — it is a lint error.

## Before you push

```bash
npm run ci
node scripts/smoke.mjs   # needs a live platform-api
```

`npm run ci` cannot tell you the backend renamed a field, because the types are
generated from a document that can be stale. `smoke.mjs` can. Run it whenever
you touch an `api.ts`, and regenerate with `npm run platform:types`.

## Ask first

New npm dependencies. Anything that writes to a deployed environment.
