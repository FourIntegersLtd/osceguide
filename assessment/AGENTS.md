# assessment-platform — AGENTS.md

Instructions for AI coding agents working in this project. The root
`OSCE Guide/AGENTS.md` still applies; this file adds the rules for this subtree.

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
- The `reviewer` agent (opus) on every finished code change, in parallel with
  `quality-reviewer`; `/security-review` too when it moves money or touches auth.

**Model and effort**
- Sonnet for a well-specified build task; Opus for design, review, debugging an
  unknown cause, and anything that moves money or touches auth.
- Effort stays medium; raise it only for hard debugging, then drop back.

**Replies**
- Result first, 10 lines or fewer: `path:line`, how it was verified, what's
  left. No preamble, no recap, no pasting back code you just wrote.

**Auditing usage**: subagent transcripts live in
`<session-id>/subagents/*.jsonl`; a tally that skips them undercounts by ~40%.

## What this project is

The shared assessment engine (`packages/osce_assessment`) plus the LiveKit
workers being built to replace `livekit/packages/livekit_b2c_worker` and
`livekit_b2b_worker`. See `README.md` for the architecture and the three-layer
domain model.

The `assessment/` folder of the osceguide repository. Python 3.11, Poetry, pytest, flat `packages/<name>/` layout
mirroring the legacy `livekit/packages` convention.

## The rule that matters most

The engine is consumer-agnostic. Never add B2C, B2B, BMJ, employer, tenant or
organisation awareness to `packages/osce_assessment`. Consumer identifiers pass
through `AssessmentAttempt.attempt_context` as opaque strings.

If you find yourself wanting a branch on who is calling, the answer is almost
always a different `EvaluationPolicy`, a different `ScenarioProvider`, or a
different `AIInteractionProfile` supplied by the consumer.

`tests/test_no_consumer_leakage.py` enforces this. Do not weaken it, widen the
`compat/` quarantine, or skip it to make a change pass. If a change genuinely
needs a new allowance, raise it rather than editing the guard.

Legacy exam vocabulary (`app_type`, and the strings `sca`/`plab`/`casc`/`ortho`)
belongs only in `compat/`. The engine takes a framework id. Consumers call
`compat.framework_id_for_app_type` while translating their own request shapes;
the engine must never import `compat` itself.

## Always do

- Test-first. The engine must stay runnable with no LiveKit server, no LLM key
  and no database: use `FakeInteractionAdapter` and the doubles in
  `osce_assessment.testing`.
- Test behaviour and contracts, not implementation details.
- Keep the engine's dependency surface at pydantic only. Clients, transports
  and storage are injected through the ports in `contracts/ports.py`.
- Split files approaching ~200 lines.
- Add new ports as `typing.Protocol`, and a matching in-memory double.
- Accept sync or async port implementations; await through
  `runtime._awaitable.maybe_await`.

## Ask first

- New dependencies of any kind, including dev dependencies.
- Changing a port signature that a worker package already implements.
- Anything that changes scoring behaviour for an existing consumer.
- Database migrations in the backends.
- Running **Promote workers to production**, or anything else that changes the
  `assessment-platform` namespace.

## Never do

- Import `openai`, `anthropic`, `instructor`, `livekit`, a database client or a
  web framework inside `packages/osce_assessment`.
- Read `app_type` outside `compat/`, or import `compat` from engine code.
- Put scoring concerns (model, prompt, thresholds) on a `CompetencyFramework`,
  or result shape (domains, competencies, scale) on an `EvaluationPolicy`.
- Modify the frozen `livekit/` project from here.
- Commit or push unless explicitly asked.

## Worker packages, environments, cutover, tutor

Worker boundaries, debrief rules, deploys (staging and production), the laptop-steals-sessions
trap, cutover discipline and the Athena traps live in `.claude/rules/attempt-engine.md`,
`tutor-ai.md` and `marking-results.md`, loaded when you touch `assessment/`. The boundary rules
are enforced by tests in `tests/`; never weaken a guard.

## Owners

Who owns which path: `.claude/OWNERS.md`.

| Area | Owner agent | Proof recipe |
|---|---|---|
| The workers, `voice_infra`, `hosting/`, `k8s/`, engine runtime, contracts and testing | `attempt-engine-owner` | `verify-attempt-engine` |
| The engine's marking half: `osce_assessment/{evaluation,schemas}` and the marking prompts | `marking-owner` | `verify-marking` |
