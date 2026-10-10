---
paths:
  - "web/src/foundation/**"
  - "web/src/surfaces/**"
  - "web/src/app/**"
  - "web/src/domains/{train,marketing}/**"
  - "web/src/capabilities/*.ts"
  - "web/scripts/**"
  - "web/e2e/**"
  - "api/app/features/dashboard/{service,service_performance,service_achievements,router_achievements}.py"
---
# Web foundation: what to know

Owner: `web-foundation-owner`. Proof: platform-web `verify` skill (`web/.claude/skills/verify/`).
Other owners own the behaviour of their screens; this owner owns how everything is built.

## The one rule
Tiers import downwards only, lint-enforced: `app -> surfaces -> domains -> capabilities -> foundation`.
A capability may not import a domain or surface; take arm-specific things as a prop or from
`useSurface()`. A screen only consumers see: `domains/train`; only institutions: `domains/assess`;
both: `capabilities/<name>`; a button, card or token: `foundation/ui`; an API call: the owning
slice's `api.ts`; a route: `app/**`, composing and holding no logic. A new capability needs a
`capability.ts` declaring its `surfaces` and a `capabilities/registry.ts` entry.

## Non-negotiable
- One HTTP path: `platformRequest` from `foundation/platform-client`. No axios, no bare `fetch`.
- Branch on `PlatformError.code`, never `message`.
- Every load goes through `useAsync` + `AsyncBoundary`; a failure must never render as "no data".
- Colours come from tokens (`bg-canvas`, `text-ink`, `bg-accent`), never `bg-blue-600`; read
  `docs/DESIGN.md` for UI work (no black borders or black text).
- The exam clock is the server's. Strict types, no `any`.
- Do not hand-declare API types: regenerate (`make openapi`, `npm run platform:types`, `npm run types`).
  `schema.d.ts` is one generated file; one writer at a time.

## Traps a browser run has hit
- `/app/me/**` shows the exam picker, not the page, while `users.exam_code` is null: set it for a
  local test account.
- A node test cannot import a `.tsx` (the loader strips types, not JSX): put a pure helper in a `.ts`.
- `npm run ci` cannot see a backend field rename (types come from a possibly stale document);
  `node scripts/smoke.mjs` can, against a live platform-api. Run it whenever an `api.ts` changes.
- Green CI once shipped an app that signed everyone out on reload: prove in a real browser.
- The web dev server proxies `/api/v1` to a REMOTE api unless routed locally; never create data on a
  remote server. Journeys: `docs/CORE-JOURNEYS.md`, `npm run e2e` against :8002.
- CI runs the journeys on a FRESH database: a spec that passes only on your dev DB (templates, a
  library, a plan on sale) is red there. `e2e/global-setup.ts` makes every precondition or fails
  naming the seed; reproduce on a fresh database, not the dev one.
- Node is not on the default PATH: `export PATH="$HOME/.nvm/versions/node/v22.22.3/bin:$PATH"`.
- Learner read models (home, performance, achievements) are in api `dashboard/`; they exist only to
  feed these screens. A stored rubric structure is read via `rubrics.service`, never directly.
- This is not the Next.js you know: read `node_modules/next/dist/docs/` before writing code.
- Open items: `docs/BACKLOG.md`; delete a row when you land it.
