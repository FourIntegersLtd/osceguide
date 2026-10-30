# OSCE Guide — AGENTS.md

Instructions for AI coding agents working anywhere in this workspace. Claude
Code and Cursor both load this file from the root. Each repo below has its own
`AGENTS.md`: read it before editing that repo.

## Project overview

Medical exam-practice platform with three arms: consumers practising for an
exam (train), institutions running and marking exams (assess), and employers
(hire, which is institution exam mode). Stack: Next.js (App Router),
TypeScript, Tailwind, FastAPI, SQLAlchemy, Postgres, Python 3, Poetry, pytest,
LiveKit.

## Repo map

One repository, `FourIntegersLtd/osceguide`, with one folder per app. Each app
deploys on its own, only when its own folder changes:

| Folder | What it is | Staging | Production |
|---|---|---|---|
| `api/` | platform-api, the one backend (FastAPI). Replaces b2c-api and b2b-api | Railway, every push to `main` touching `api/` or the engine | Railway, from `production-api` ("Promote api to production") |
| `web/` | platform-web, the one frontend (Next.js) | Vercel, every push to `main` touching `web/` or `api/openapi.json` | Vercel, from `production-web` ("Promote web to production") |
| `assessment/` | The marking engine (`packages/osce_assessment`) and the LiveKit assessment and assistant workers | K3s, after CI assessment passes on `main` | K3s, from `production-workers` ("Promote workers to production") |

The api installs the engine straight from `assessment/packages/osce_assessment`
(a Poetry path dependency), so an engine change and the api change that uses
it land in one commit, with no tag. An engine change therefore runs CI api too
and redeploys the api's staging.

**Retiring**, outside this repository: do not start new work there.

| Repo | Status |
|---|---|
| `b2c-api/`, `b2b-api/` in the old backend repo | Legacy backends, still serving the live site until the switch |
| `livekit/` | Frozen legacy workers, no traffic. Never edit or push. Retirement: `livekit/README.md` |

## Where agent files live

**The rule:**

- Anything that spans apps or is about how agents work goes at the root:
  owner agents, rule files, skills, the ownership table and this map.
- Anything describing one app's code goes in that folder's `AGENTS.md` (rules every change
  obeys), and area-specific "what to know" goes in `.claude/rules/<area>.md`, changed in the same
  commit as the code.

Three pieces, one mechanism each:

| Piece | Where | What it is |
|---|---|---|
| Area notes ("what to know") | `.claude/rules/<area>.md`, with `paths:` frontmatter | Loads on its own when a session touches those paths. 11 areas, 150 lines each at most |
| Skills ("how to work") | `.claude/skills/<verb>/SKILL.md` | `build-feature`, `fix-bug`, `verify-*`, `make-slide-deck` |
| Owners ("who does it") | `.claude/agents/<area>-owner.md` | "You own these paths; read the rule file; prove with the verify skill" |

| File | Scope |
|---|---|
| `AGENTS.md` (this file) | Repository map, principles, cost discipline |
| `.claude/OWNERS.md` | Path glob to owner. `api/tests/guards/test_ownership.py` fails if a tracked source file matches no row or two |
| `.claude/rules/*.md` | The 11 area notes: identity-tenancy, money, attempt-engine, marking-results, exam-day, station-content, media-community, tutor-ai, comms, staff-console, web-foundation |
| `.claude/agents/*-owner.md` | The 7 owners (see Owners) |
| `.claude/skills/build-feature/`, `fix-bug/` | The way to work: build tests-first with arm and sibling checks; fix a bug at its root and close the CI gap that let it through |
| `.claude/skills/verify-{attempt-engine,marking,institution,access,content,staff-console}/` | Proof recipes; web/'s is its own `verify` skill |
| `.claude/skills/fix-experience-gaps/` | Retiring once `docs/EXPERIENCE-GAPS.md` is closed |
| `.claude/agents/slide-deck-author.md` | Makes teaching slide decks from OSCE cases: fact-check, voice, publish. Runs the `.claude/skills/make-slide-deck/` pipeline |
| `.claude/agents/quality-reviewer.md` | Second check on every code change: repetition, reuse, structure, tiers, dead code. Not correctness (`reviewer`) |
| `.claude/hooks/quality-gate.sh` | Stop hook: once per changed code diff, asks the main agent to run `quality-reviewer` and `reviewer` (opus) and act on them; money, auth, migration and CI paths also need `/security-review` and the user's review |
| `.claude/evals/reviewer/` | Past shipped bugs as a scored test of the `reviewer` agent; rerun after changing a reviewer prompt, failure notes or model |
| `.cursor/rules/critical-thinking-partner.mdc` | Always on: push back on risk, plan first for large work |
| `api/AGENTS.md` | Backend rules, commands, traps, ownership |
| `web/AGENTS.md` (+ `docs/DESIGN.md`) | Frontend tiers, non-negotiables, design language |
| `web/.claude/skills/verify/` | Prove a web/ change in a real browser |
| `.github/workflows/` | One CI and one promote workflow per app, filtered by folder |
| `assessment/AGENTS.md` | Engine boundaries (test-enforced) |
| b2b-api's and `livekit/k8s/`'s `AGENTS.md` | Legacy, in the old repos. Retire with their code, don't extend |

`CLAUDE.md` files contain only `@AGENTS.md`, so Claude Code and Cursor read
the same text.

## How to work

New behaviour goes through `build-feature` (spec matrix, arm check, sibling check, impact, failing
tests, smallest build, proof, review, ledger). A defect goes through `fix-bug` (failing test, root
cause, name the kind of bug and the CI check that should have caught it, add that check). Both start
as, or hand to, the owner of the paths you touch.

## Owners

An owner is a subagent that starts from one area's rule files and proves its work before calling it
done. One owner per file: `.claude/OWNERS.md` is the table, and the guard keeps it complete.

| Owner | Rule files it reads | Area | Proof recipe |
|---|---|---|---|
| `access-owner` | identity-tenancy, money, comms | Sign-in, sessions, SSO, invitations, entitlements, billing, growth and referrals, the email outbox, inbox api | `verify-access` |
| `institution-owner` | exam-day | Exam mode (incl. hire), circuits, roster, tenancy, programmes, org read models, `domains/assess`, hire and partner surfaces | `verify-institution` |
| `marking-owner` | marking-results | Scoring, rubrics, authored exams, results and reviews, engine marking prompts, legacy oracles | `verify-marking` |
| `attempt-engine-owner` | attempt-engine, tutor-ai | Attempts, voice, the `/api/worker/*` contract, assessment/ workers, assistant and tutor memory, web runners, feedback, debrief, transcripts | `verify-attempt-engine` |
| `content-owner` | station-content, media-community | Station library, templates, generation, authoring, media, community, marketplace, peer practice, CV, public site | `verify-content` |
| `staff-console-owner` | staff-console | Health and ops, background jobs, alembic, worker entry, `domains/platform`, staff-* capabilities | `verify-staff-console` |
| `web-foundation-owner` | web-foundation | Foundation, surfaces, tiers, design system, `app/`, learner dashboard, marketing, inbox web | platform-web `verify` |

Every platform-api slice has one owner. Where two claim a file: attempt-engine starts rooms,
marking computes scores, institution runs the workflow, and a screen's behaviour belongs to its
area's owner while web-foundation owns how it is built.

To add an owner or area:

1. Agent file `.claude/agents/<area>-owner.md` and rule file `.claude/rules/<area>.md`
   (with `paths:`, 150 lines at most).
2. Proof recipe `.claude/skills/verify-<area>/SKILL.md`: each kind of change to a level of proof,
   then the exact commands and the traps.
3. Rows in `.claude/OWNERS.md`; run `cd api && poetry run pytest tests/guards/test_ownership.py -q`.
4. A row in this file and in the Owners table of the owned app's `AGENTS.md`.

## Commands

```bash
# platform-api (from api)
docker compose up -d && poetry run alembic upgrade head
poetry run python scripts/seed_platform.py   # an unseeded DB refuses every attempt
make start                                   # :8002
make ci

# platform-web (from web)
npm run dev
npm run ci

# assessment engine and workers (from assessment)
poetry run pytest -q
```

Node is not on the default PATH here:
`export PATH="$HOME/.nvm/versions/node/v22.22.3/bin:$PATH"`.

Retiring stack, only while it still serves the live site:

```bash
# in the old backend checkout, not this repository
cd b2c-api && make start && poetry run pytest -q
cd b2b-api && make start && poetry run pytest -q
```

## Boundaries

### Always do

- Read the nested `AGENTS.md` when editing that repo.
- Keep diffs focused. Split files by responsibility, not line count, and merge
  micro-files when you touch them.
- Use strict types, no `any`.
- Fix the lint and type errors you introduce.

### Ask first

- New npm or Poetry dependencies, DB migrations, deleting routes, auth or
  features, and force-push.

### Never do

- Commit secrets (`.env`, `*.pem`, `serviceAccountKey.json`).
- Commit or open PRs unless asked.
- Edit or push `livekit/`.

## Engineering principles

Borrowed from [pstack](https://github.com/cursor/plugins/tree/main/pstack). When you apply one, say which decision it changed.

- **Laziness protocol.** Prefer deletion and the smallest change that solves the problem. No new layer, wrapper, seam or abstraction without a second real caller.
- **Subtract before you add.** Remove dead code and obsolete paths first, then build on the simpler base.
- **Migrate callers, then delete.** A new internal API replaces the old one in the same change; no compatibility shims left behind.
- **Fix root causes.** Reproduce first, trace to the cause, fix it there. No guards that only silence the symptom.
- **Test behaviour, not implementation.** Call code the way its users do and assert a literal expected value. A test that would pass with every import stubbed out is deleted.
- **Prove it works.** Done means the real artifact was checked (the running app, the stored row, the rendered screen), not that CI or the compiler passed. Green CI has hidden a sign-out-on-reload bug and 20 unwired domain rules here.

## Git workflow

Do not commit or push unless explicitly requested. Never force-push `main`/`master`.

## Cursor token usage

Repo ignore files reduce indexing noise (~800MB slides/audio blocked):

| File | Role |
|------|------|
| `.cursorignore` | Hard block — secrets, logs, slide audio, podcast, binaries, lockfiles |
| `.cursorindexingignore` | Excludes slides tree, public assets, fonts from `@codebase` search |

After changing ignore files: **Command Palette → Cursor: Resync Index**.

**Settings (all projects):** Cursor Settings → Indexing → Ignore Files — add `**/.env`, `**/*.pem`, `**/serviceAccountKey.json`. Disable include open tabs / recent edits if you `@` files manually. Default to Composer/Sonnet; reserve premium models for hard bugs.

**Habits:** new chat per task; `@file` over `@codebase`; Agent only for multi-file work; Tab/Cmd+K for small edits.

## Token discipline (measured, not guessed)

Cost = **context size x request count**. Every tool call replays the whole
context, so a call that costs 5k early in a session costs 76k late. Measured on
2026-09-24: one session reached 758k context and moved 575M tokens over 2,346
requests; 41% of that landed in an 18-minute window of 16 concurrent agents.

A warn-only `PreToolUse` hook (`~/.claude/hooks/cost-guard.sh`) reminds you of
these at the moment you break them. It never blocks -- heed it anyway.

### Subagents

- **`Explore` for anything read-only** -- audits, parity checks, "find where X
  lives". It is read-only and reads excerpts, not whole files.
- **Never `general-purpose` for a read-only sweep.** It boots with the full tool
  schema plus every skill description (~24k tokens before it does any work).
- **Always set `model`** on an Agent call: `haiku` or `sonnet` for sweeps and
  greps. Unset means it inherits the parent's premium model.
- **Never pass `model` to an owner agent.** Owners run on their frontmatter model
  (sonnet). Opus judgement lives in `reviewer`, run on the finished diff; one owner
  overridden to opus was 12% of a week's spend (2026-10-30).
- **Cap fan-out at 3-4 concurrent.** 16 at once finished no sooner than a
  smaller batch and cost 39% of the day's usage.
- Subagent transcripts live in `<session-id>/subagents/*.jsonl`. Any per-session
  cost tally that ignores that directory undercounts by ~40%.

### Main thread

- **Batch tool calls.** Combine related greps/reads into one `Bash` call; call
  count is the multiplier, not command size.
- **Long output goes to a file**, then read the tail -- never pipe a large dump
  straight into context.
- Sessions auto-compact at 200k (`autoCompactWindow` in `~/.claude/settings.json`)
  even on a 1M model. Do not raise it without a reason.
- `/clear` at task boundaries; one writing session per repository at a time.

## Updating this file

Update it when an app is added or retires, when an owner or rule file is added, or when an
agent file moves.
