# platform-web — AGENTS.md

Read `README.md` first, then
`docs/adr/0001-one-app-shared-capabilities-three-surfaces.md`.

## Token discipline (read first — measured, not guessed)

Cost = **context size x request count**. Every tool call replays the whole
context, so the same Bash call cost ~5k tokens early in a session and ~76k late
in it. Measured on this project: one session grew 46k -> 758k, never
compacted, and moved 575M tokens over 2,346 requests; 41% of that day's cost
landed in 18 minutes when 16 `general-purpose` subagents ran at once on a
premium model for read-only audit work. Skills and MCP were not the cause.

**Context**
- Stay on a 200k model; auto-compact at 200k (`.claude/settings.json`). Never
  a 1M model for ordinary work.
- `/compact` at a natural break, `/clear` between unrelated tasks. One writing
  session per repository at a time.

**Calls**
- Issue every independent read in ONE turn, as parallel calls. Batch related
  greps into one Bash call.
- Locate before you read (grep, `git ls-files | grep`), then read only the line
  ranges you need. Skip lockfiles, node_modules, build output, generated types.
- Never re-read a file you already read unless it changed, nor after your own
  edit "to verify": the edit tool reports failure.
- Long output goes to a file; read the tail and check the exit code:
  `cmd > "$TMPDIR/out.txt" 2>&1; echo "exit=$?"; tail -40 "$TMPDIR/out.txt"`

**Subagents**
- Read-only sweeps (audits, parity checks, "where is X") needing more than 2-3
  greps: `Explore` with `model: "haiku"` (or `"sonnet"` for judgement).
- Never `general-purpose` for read-only work: it boots with ~24k tokens of tool
  schema and skill descriptions and inherits the parent's premium model.
- Always set `model` on an Agent call.
- At most 3-4 subagents at once; 16 in parallel finished no sooner.
- Test/lint/type runs and edits you have already fully specified: the `worker`
  agent (haiku, `.claude/agents/worker.md`), which returns only failures.
- The `reviewer` agent (opus) only when the task asks for review or the change
  moves money or touches auth.

**Model and effort**
- Sonnet for a well-specified build task; Opus for design, review, debugging an
  unknown cause, and anything that moves money or touches auth.
- Effort stays medium; raise it only for hard debugging, then drop back.

**Replies**
- Result first, 10 lines or fewer: `path:line`, how it was verified, what's
  left. No preamble, no recap, no pasting back code you just wrote.

**Auditing usage**: subagent transcripts live in
`<session-id>/subagents/*.jsonl`; a tally that skips them undercounts by ~40%.

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

What is still missing is in `docs/BACKLOG.md`; delete a row when you land it.

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
  `bg-blue-600` picks one arm's side and breaks the other three skins. For any
  UI work, read `docs/DESIGN.md`: tokens, type scale, radii, reading tones.
- **The exam clock is the server's.** Read `remaining_seconds` and
  `phase_ends_at`. Never run an authoritative countdown in the browser.
- Strict types. No `any` — it is a lint error.

## Before you push

```bash
npm run ci
node scripts/smoke.mjs   # needs a live platform-api
```

After a backend schema change: `make openapi` in platform-api, then
`npm run platform:types`, then `npm run types`. One session at a time:
`schema.d.ts` is one generated file, and parallel writers collide.

`npm run ci` cannot tell you the backend renamed a field, because the types are
generated from a document that can be stale. `smoke.mjs` can. Run it whenever
you touch an `api.ts`, and regenerate with `npm run platform:types`.

## Owners

| Area | Owner agent | Proof recipe |
|---|---|---|
| How everything is built: foundation, surfaces, tiers, design system; `domains/train`, `domains/marketing` | `platform-web-owner` | `verify` skill (`.claude/skills/verify/`) |
| `domains/assess`, `domains/platform` behaviour | `institution-owner` | `verify-institution`, then `verify` |
| `foundation/session`, `capabilities/account`, `staff-growth`, `domains/partner`, middleware | `access-owner` | `verify-access`, then `verify` |
| `capabilities/stations`, `authoring`, `media`, `staff-media`, `staff-moderation`, `community`, `peer-practice` | `content-owner` | `verify-content`, then `verify` |
| `foundation/livekit`, `capabilities/onboarding`, `help` | `voice-station-owner` | `verify-voice-station`, then `verify` |

Owner agents live in the workspace root's `.claude/`.

## Traps a browser run has hit

- `/app/me/**` shows the exam picker, not the page, while `users.exam_code` is
  null. Set it for a local test account before you drive a consumer screen.
- A slot's attempt must be `kind = 'exam_slot'` (the `kind_matches_reference`
  check). To put marked work in front of an examiner locally, copy a marked
  attempt as an exam-slot attempt: `.claude/skills/verify/features/feedback-fixture.sql`.
- A node test cannot import a `.tsx` file (the loader strips types, not JSX). Put a pure helper a test
  needs in a `.ts` file beside the component.
- A local database can hold exams and rubrics but no stations or marked attempts. A review screen still
  renders for a slot with no attempt; `features/rubric-builder.md` has a fixture that needs neither.
- Feedback and forms are drawn from the rubric (`capabilities/feedback/rubric.ts`,
  `domains/assess/results/reviewForm.ts`). Never branch on an exam code; a rating
  is coloured by its position in the scale, not by its letter.

## Ask first

New npm dependencies. Anything that writes to a deployed environment.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
