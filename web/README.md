# platform-web

The single frontend for every OSCE Guide product: consumer practice, an
institution's examinations, and the employer arm. It talks to one backend
(`platform-api`) and to the LiveKit workers in `assessment-platform`.

It replaces `frontend/`, which is two source trees — `src/b2c` and `src/b2b` —
inside one app. That project is untouched and still runs; this one is stood up
beside it the way `platform-api` was stood up beside `b2b-api` and `b2c-api`.

## Why it is shaped like this

`docs/adr/0001-one-app-shared-capabilities-three-surfaces.md` is the argument.
The short version: the three arms are not three products. The backend has no
notion of an arm — it has exams, organisations with programmes, entitlements,
and **one `attempts` table** that consumer practice, a mock station, a debrief,
an exam slot and a peer session all write to. A frontend that renders that loop
three times is fighting the backend it consumes.

## The tiers

```
  src/app          routes only — a page composes, it does not decide
  src/surfaces     one shell per arm: train · assess · hire · platform
  src/domains      arm-specific work: train, assess, hire
  src/capabilities mountable by ANY surface
  src/foundation   ui · session · platform-client · livekit · hooks
```

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

### Adding a capability to another arm

Adding the study library to institutions was, in full:

1. `surfaces: ["train", "assess"]` in `src/capabilities/media/capability.ts`
2. `src/app/assess/[orgSlug]/library/page.tsx`, four lines

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
npm run dev                   # :3100
```

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
npm run ci                    # types, lint, unit tests
node scripts/smoke.mjs        # every call a screen makes, against a live API
```

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
