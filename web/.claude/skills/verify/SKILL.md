---
name: verify
description: Prove a platform-web change works in a real browser against a local platform-api — launch both, sign in as a test account, drive the screen, and keep screenshots, ARIA snapshots and a request log as evidence. Use after any change to a platform-web screen, route, session or voice flow, before saying it works; green CI has shipped an app that signed everyone out on reload.
---

# Verify platform-web

The web app (Next.js, :3100) proxies to platform-api (FastAPI, :8002). Checks
drive system Chrome through `playwright-core` with a thin harness, and every
run leaves evidence in `.verify/<run-id>/` (gitignored).

Before driving a feature, read its file in `features/` — the handles and
gotchas there are measured, not guessed.

## Launch

Start only what is not already up (run `doctor.mjs` first), and record the PID
of whatever you start so Cleanup kills that and nothing else.

```bash
export PATH="$HOME/.nvm/versions/node/v22.22.3/bin:$PATH"   # npm is not on PATH otherwise

# API (from api)
make db-up                                   # postgres :5433, redis :6380
nohup make start > "$TMP/api.log" 2>&1 & echo $! > "$TMP/api.pid"

# Web (from platform-web) — Turbopack. `npm run dev:webpack` only if it panics:
# webpack compiles each route 3-10x slower and its cache grows to gigabytes.
nohup npm run dev > "$TMP/web.log" 2>&1 & echo $! > "$TMP/web.pid"
```

A migrated database is empty: `poetry run python scripts/seed_platform.py`
seeds exams. The test account comes from `make bootstrap-admin
EMAIL=<name>@example.com`, and `node scripts/seed-demo-org.mjs` gives it an
institution. Point the harness at it with `VERIFY_EMAIL` / `VERIFY_PASSWORD`.
A platform admin must have an authenticator: set `ADMIN_TOTP_SECRET` (or put
it in `~/.osce-staging-accounts.env`) and re-run bootstrap so the harness can
compute the code.

**Never sign in as a real person.** The local database holds imported
production users; only `@example.com` accounts are fair game.

## Doctor

```bash
node .claude/skills/verify/doctor.mjs
```

Read-only. Checks Chrome, postgres, `GET /health`, `GET /login` (the first hit
compiles for ~15s), and that the test account can sign in. Each failure prints
its fix. Do not drive anything until it says `ready`.

## Drive

Write a throwaway script in `.verify/` and run it from `web/`
(`playwright-core` resolves only there):

```js
import { start, signIn, open, proof, finish } from "../.claude/skills/verify/harness.mjs";
const run = await start("sittings");
await signIn(run);                                   // lands on /app/me
await open(run, "/app/kings/sittings");              // waits for the first <h1>
await proof(run, "sittings");
process.exitCode = (await finish(run)) ? 1 : 0;
```

- `open(run, path, { ready: (p) => p.getByRole(...), settle })` — pass `ready`
  when the screen has no `<h1>` or the `<h1>` shows before the data.
- Locate by role and name (`getByRole("link", { name: "Trainees 4" })`), the
  same names the ARIA snapshots print. No CSS selectors.
- Count requests, not just outcomes: attach `run.page.on("request", …)` to
  the endpoints under test. Loops that render correctly are still bugs — the
  onboarding screen once opened 3,144 voice sessions in 15 seconds while
  looking perfectly fine.
- Just edited source? The dev server recompiles, and the first run can load
  a half-built chunk (`pageerror: Invalid or unexpected token`, stuck on
  "Checking your session"). Rerun once before believing it.
- Read-only by default. Anything that creates data (a sitting, a station)
  uses the test account's own organisation, and says so in the run log.

## Board vs app

A screen with a board in `docs/institution-overhaul/boards/` is proved with `e2e/support/board-diff.ts`
(`npx playwright test e2e/assess/board-home.spec.ts`, also in `npm run e2e:assess`): pixel diff, computed styles, hover,
desktop 1440 and mobile 760, PNGs under `docs/institution-overhaul/verify/board-diff/`. If Playwright says port 3101 is
in use, an old `next dev --port 3101` is still running: kill it or set `E2E_REUSE_SERVER=1`. The empty-org state of
Main is `node scripts/seed-demo-org.mjs --empty`.

## Evidence

Each run writes to `.verify/<ISO-time>-<label>/`:

| File | What it proves |
|---|---|
| `<name>.png` | full-page screenshot |
| `<name>.aria.txt` | ARIA tree of `<main>` — diffable, and what to quote |
| `run.log` | every step with status and final URL, then `problems:` |

`problems` collects page errors, console errors, 404s and any response ≥ 500. A run
with problems exits non-zero. Quote the evidence path when reporting.

## Cleanup

```bash
kill "$(cat "$TMP/web.pid")" "$(cat "$TMP/api.pid")" 2>/dev/null
```

Kill only PIDs you recorded — the user may have their own servers on these
ports. `pkill -f "next dev"` takes theirs down too. Leave `.verify/` alone;
it is the evidence. Delete your throwaway scripts in it.

## Helpers

- `harness.mjs` — `start`, `signIn`, `open`, `proof`, `finish`; env overrides
  `VERIFY_WEB_URL`, `VERIFY_API_URL`, `VERIFY_CHROME`, `VERIFY_EMAIL`,
  `VERIFY_PASSWORD`.
- `doctor.mjs` — preflight, above.
- `features/README.md` — the feature map; start there.
- `scripts/smoke.mjs` (repo) — API-only contract walk; complements, not
  replaces, a browser run.
