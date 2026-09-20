# platform-web

The single frontend for every OSCE Guide product: consumer practice, an
institution's examinations, the employer arm and the publishing partners. It talks to one backend
(`platform-api`) and to the LiveKit workers in `assessment-platform`.

It replaces `frontend/`, which is two source trees — `src/b2c` and `src/b2b` —
inside one app. That project is untouched and still runs; this one is stood up
beside it the way `platform-api` was stood up beside `b2b-api` and `b2c-api`.

## Why it is shaped like this

`docs/adr/0001-one-app-shared-capabilities-three-surfaces.md` is the argument.
The short version: the arms are not separate products. The backend has no
notion of an arm — it has exams, organisations with programmes, entitlements,
and **one `attempts` table** that consumer practice, a mock station, a debrief,
an exam slot and a peer session all write to. A frontend that renders that loop
three times is fighting the backend it consumes.

## Where things are

```
osceguide.com/              marketing: the landing, /exams/[exam], /institutions, /compliances/*
osceguide.com/login         one sign-in, for every product
osceguide.com/app/me/…      somebody's own practice
osceguide.com/app/<slug>/…  an organisation — its `org_type` picks the shell
osceguide.com/staff/…       the OSCE Guide console
```

A person's own practice is a workspace, addressed exactly like an
organisation's. No arm appears in a path, so adding one adds no routes. The
argument is `docs/adr/0002-url-grammar.md`; the short version is that every
product with a personal space and a team space is shaped this way, and the
alternative forced a special case into every routing decision.

## The tiers

```
  src/app          routes only — a page composes, it does not decide
  src/surfaces     one manifest per arm: train · assess · hire · partner · platform
  src/domains      arm-specific work
  src/capabilities mountable by ANY surface
  src/foundation   ui · charts · table · routing · session · platform-client · livekit · hooks
```

An arm is declared as data — its label, which workspace kinds reach it, its
navigation, and which pages it answers — and holds no React, which is what lets
`src/surfaces/registry.test.ts` assert the whole shape of the product's
navigation without rendering anything: that no two arms claim the same kind of
workspace, that every arm answers every destination its own menu offers, and
that Hire is still Assess's screens rather than a fork of them.

Each tier may import only downwards, and `eslint-plugin-boundaries` fails the
build otherwise. Prove it:

```bash
echo 'import "@/domains/assess/api";' > src/capabilities/media/_x.ts
npx eslint src/capabilities/media/_x.ts   # capability may not import domain
rm src/capabilities/media/_x.ts
```

**The rule that matters is the one on `capabilities`.** A capability may not
import a surface or a domain. That is what keeps help, study material, the
station library and discussion mountable by institutions. In the old client the
help section became consumer-only one import at a time and nothing caught it.

### Adding an arm

1. Add its id to `SURFACES` in `src/capabilities/surface.ts` — a compile error
   until step 2, because the registry is a `Record<Surface, SurfaceManifest>`.
2. Add `src/surfaces/<arm>/surface.ts` (the manifest) and `screens.tsx`.
3. List the arm in the `surfaces` of each capability it should mount.
4. Update the `registry.test.ts` snapshot.

No route files, no URL prefix, no redirect. Partner was added this way.

### Adding a capability to another arm

Adding the study library to institutions was, in full:

1. `surfaces: ["train", "assess"]` in `src/capabilities/media/capability.ts`

That is all of it now: there is one `/app/[workspace]/library` route and
`<Capability>` decides from the same registry the navigation reads, so a page
can never be reachable by URL while absent from the menu, or the reverse.

Navigation, the href prefix and the help assistant's knowledge of the section
all follow from the registry. `src/capabilities/registry.test.ts` pins it, so
narrowing it back to consumers fails a test rather than quietly removing a
section from an institution.

## Running it

Three things have to be up: Postgres and Redis, the API, and this.

```bash
# 1. the backend (the current checkout is backend-tutor-memory/platform-api)
cd ../backend-tutor-memory/platform-api
cp .env.example .env          # see "Talking to the workers" before editing
make db-up && make migrate
make start                    # :8002

# 2. this
npm install
cp .env.example .env.local
npm run dev                   # :3100 (Turbopack — faster local navigation)
# npm run dev:webpack         # fallback if Turbopack mis-resolves @/b2b imports
```

### Local dev performance

Slow `npm run dev`, long first **Compiling…**, or heavy navigation usually means
the workspace shell was pulling too much JavaScript into one chunk. The app now:

- loads each arm's **screen map on demand** (`loadScreenComponent` in
  `src/surfaces/screens.ts`) instead of static-importing every domain from the
  layout;
- keeps **nav footers** in `src/surfaces/navFooters.ts` so `SurfaceShell` never
  imports the screen registry;
- **lazy-loads help** (LiveKit) via `LazyHelpPanel` on institution-style shells,
  matching `LazyB2CHelpDock` on train.

Staff routes already avoided `SurfaceShell` — see `src/app/staff/layout.tsx`.

**Tips**

- Prefer `npm run dev` (Turbopack). Use `npm run dev:webpack` when debugging
  `@/b2b` resolution from `frontend/src/b2b`.
- `predev` / `prebuild` symlink `frontend/node_modules` → this app's
  `node_modules` so legacy `frontend/src/b2b` imports resolve npm packages.
- Avoid running legacy `frontend/` dev at the same time if watchers feel hot.
- Rough startup timing: `node scripts/measure-dev-startup.mjs` (Turbopack) or
  pass `--webpack`.
- `npm test` includes `devPerfImports.test.ts`, which fails if the workspace
  shell regresses to a static `screens.ts` import.

Port 3100, not 3000, so the retiring `frontend/` can run at the same time. The
API's `CORS_ORIGINS` must list `http://localhost:3100`.

### A database you can sign into

A migrated database has the four exams and nothing else.

```bash
cd ../backend-tutor-memory/platform-api
poetry run python scripts/bootstrap_admin.py --email you@example.com
```

Then, from here, publish some study material through the real API:

```bash
node scripts/seed-dev-content.mjs --email you@example.com --password ...
```

### Talking to the workers

Three things have to line up, and all three are verified by `scripts/smoke.mjs`
and the steps below.

**1. The API can mint a room token.** `POST /api/v1/attempts/{id}/voice-token`
answers `voice_unavailable` until the API has `LIVEKIT_URL`,
`LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET`. The same three live in
`assessment-platform/.env`. The API mints the token and decides Cloud against
self-hosted; the browser never chooses a server.

**2. The agent names match.** The API dispatches `{family}-{mode}`, so with the
default self-hosted mode it asks for `assessment-self-hosted`. The worker
registers under `LIVEKIT_ASSESSMENT_AGENT_NAME`, which is that same string in
`assessment-platform/.env`. If they differ, a candidate joins a room and nobody
comes.

If local and deployed workers share the LiveKit project, set the API's
`LIVEKIT_AGENT_NAMESPACE` to a unique development prefix, and prepend that
prefix plus `-` to both worker agent names. Run the assistant worker as well
as the assessment worker: Practice as Patient uses the consulting-doctor role
on `assistant`, while debrief uses `assessment`. See
`../assessment-platform/README.md` for the paired startup commands.

```bash
cd ../assessment-platform && make dev-assessment
# registered worker {"agent_name": "assessment-self-hosted", ...}
```

**3. The worker can read the attempt back.** It fetches the frozen scenario from
`/api/worker/attempts/{id}` with an `X-Worker-Secret` header, so
`assessment-platform`'s `VOICE_BACKENDS_JSON` needs a `platform` entry whose
`PLATFORM_WORKER_SECRET` equals the API's `WORKER_SECRET`:

```json
"platform": {
  "base_url_env": "PLATFORM_API_URL",
  "secret_env": "PLATFORM_WORKER_SECRET",
  "secret_header": "X-Worker-Secret",
  "slot_release_path": "/api/worker/livekit-cloud-slot/release",
  "slot_extend_path": "/api/worker/livekit-cloud-slot/extend",
  "slot_payload_key": "room_name"
}
```

Check it without a browser:

```bash
curl -H "X-Worker-Secret: $WORKER_SECRET" \
  http://127.0.0.1:8002/api/worker/attempts/<attempt-id>
```

Nothing about the scenario travels through the browser: the attempt is frozen
server-side when it is created and the worker fetches it by id, so a tampered
payload cannot change what is assessed.

## Checking it

```bash
npm run ci                    # types, lint (tiers included), unit tests
node scripts/smoke.mjs        # every call a screen makes, against a live API
node scripts/walkthrough.mjs  # sign in and visit every arm, in a real browser
```

`walkthrough.mjs` is the one that catches what needs a second page load: it
found a refresh-token race that signed people out on reload, a hydration
mismatch on every gated screen, a staff console with no session gate, and a
redirect pointing at a page that does not exist. It prints each arm's
navigation and heading and checks that a consumer page asked of an institution
404s, and so does a workspace you are not in.

`smoke.mjs` is the one that catches drift a typed client cannot: the generated
schema comes from a document that can itself be stale. The capability keys in
this repo were wrong until it ran — the shells were asking for `org.team.manage`
and the backend answers `manage_team`.

## Regenerating the API types

```bash
npm run platform:types
```

Reads `../backend-tutor-memory/platform-api/openapi.json`. Point it at whichever
checkout is current; `backend/platform-api` was fifteen migrations behind when
this was written.
