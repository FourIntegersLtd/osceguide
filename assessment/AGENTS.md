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

## What this project is

The shared assessment engine (`packages/osce_assessment`) plus the LiveKit
workers being built to replace `livekit/packages/livekit_b2c_worker` and
`livekit_b2b_worker`. See `README.md` for the architecture and the three-layer
domain model.

Its own git repo. Python 3.11, Poetry, pytest, flat `packages/<name>/` layout
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
- Running **Promote to production**, or anything else that changes the
  `assessment-platform` namespace.

## Never do

- Import `openai`, `anthropic`, `instructor`, `livekit`, a database client or a
  web framework inside `packages/osce_assessment`.
- Read `app_type` outside `compat/`, or import `compat` from engine code.
- Put scoring concerns (model, prompt, thresholds) on a `CompetencyFramework`,
  or result shape (domains, competencies, scale) on an `EvaluationPolicy`.
- Modify the frozen `livekit/` project from here.
- Commit or push unless explicitly asked.

## Worker packages (as they land)

`voice_infra` is a config-driven port of `livekit_voice`: it takes a
`BackendEndpoints` value rather than a `"b2c" | "b2b"` product string, which is
the branching the legacy shared package leaked. `livekit_assessment_worker`
covers the patient and debrief interactions and must not import
`osce_assessment.prompts`, `.schemas`, `.catalog`, `.evaluation` or `.compat`,
nor name a product, station field or storage system (guarded by
`tests/test_assessment_worker_boundaries.py`). It receives rendered
instructions from the backend's bootstrap route and delivers transcripts back;
scoring happens backend-side. Tools it may expose are named in the profile
(`tools`) with their rendered data in `tool_context`; implementations live in
its `tools.py` and must stay about transcripts and the room, never products. `livekit_assistant_worker` covers help,
onboarding, dashboard and consulting-doctor and must not import
`osce_assessment.runtime`, `.evaluation`, `.schemas`, `.catalog` or
`.compat`, nor the assessment worker (guarded by
`tests/test_assistant_worker_boundaries.py`). Per-session-type decisions live
only in its `modes.py` table (`tests/test_assistant_worker_modes.py` fails on
a string comparison against a session type anywhere else, and on any FAQ or
session-prompt module reappearing). Instructions (with the full FAQ rendered
in for help sessions; there is no FAQ search tool), greetings and
speech-to-speech instructions all arrive rendered in the bootstrap; the
templates live in `backend/b2c-api/b2c/shared/services/assistant_prompts/`
and the content they render (FAQ packs per exam and surface, greetings,
persona, onboarding scenes) in `.../assistant_content/`, selected by the
client profile the frontend declares (surface, current route, navigation
catalog). The worker never sees a navigation label, a product name or an
exam id (`tests/test_assistant_worker_no_product_vocabulary.py`).
The UI-guidance toolset began as a port of the legacy worker's and has since
diverged: one module per concern under `ui_guidance/`, pointers written inline in
the model's reply as `[POINT:x,y:Label]` and stripped in `GuidanceAgent`'s
`tts_node`, and a progress panel driven from `progress.py`. Keep
`ui_guidance/contracts.py` in step with the frontend `livekit-ui-guidance`
package — `tests/test_ui_guidance_contract_drift.py` reads the TypeScript and
fails when they disagree.

Only announce a tool with `ctx.update` when it is genuinely slow. The first
update makes the call non-blocking, so its result is deferred to the next idle
moment; on a millisecond-long action that delays the sentence the user is waiting
for. The policy table in `ui_guidance/progress.py` is where that decision lives.

Model ids, voices and spoken style are `voice_infra.speech.SpeechSettings`
(`VOICE_<FIELD>` env). Do not hardcode a model or a persona name in a worker.
Reasoning effort is a setting too, and defaults to `none`: live voice has no
room for a model that thinks before it speaks.

Every live persona opens by naming the role it is cast in, using the shared
block from `osce_assessment.prompts._blocks`;
`tests/test_prompt_role_locks.py` fails on a prompt that does not say whose
lines the model speaks. Greetings come from
`osce_assessment.prompts.greetings` so both backends speak the same ones.

Re-sending a role reminder on every turn was tried and measured away: it bought
nothing on the simulated patient and made the consulting doctor measurably
worse. Do not reintroduce it without running `scripts/model_bench.py` first.

The debrief tutor walks the trainee through the station's management plan
together (PEARLS-style, not Pendleton), and may briefly play the patient for one
moment the trainee asks to practise; the `exception` line in its role lock is
the only such allowance. It was chosen by `scripts/debrief_bench.py`, which runs
prompt variants against simulated trainees played by Claude. Change the debrief
prompt only after running that against the baseline (about $2 for 16 debriefs).

The debrief runs on a ten-minute clock, as the consulting doctor runs on its
own: `osce_assessment.prompts.debrief_pacing` writes the marks and the prompt's
`<pacing>` block, platform-api sends the plan as `tool_context["pacing"]` with
`check_time` in `tools`, and the assessment worker's adapter starts the clock
when the session opens. The clock itself (`InteractionClock`, `PacingPlan`,
`build_check_time_tool`) lives in `voice_infra.pacing`, shared by both workers.

`hosting/` runs one worker per process, selected by `OSCE_LIVEKIT_WORKER`;
add a worker to `hosting/workers.py` when it lands. The container starts it
directly (`python -m hosting.run_worker start`, PID 1). Never put a shell, make
or a supervisor in front of it: the stop signal must reach the LiveKit SDK, or a
terminating pod keeps taking new sessions until it is killed mid-consultation.

The LiveKit pins must match `livekit/pyproject.toml` exactly, including the
documented `anthropic >=0.41,<1.0.0` httpx constraint.

## Environments and deploys

Two environments on one K3s cluster, built from `k8s/base` plus an overlay
(`k8s/README.md` has the whole flow):

- **staging**: namespace `assessment-platform-staging`, LiveKit project
  `new-test-agent`, backend `staging-api.osceguide.com`. Every green `main` rolls
  here by itself (`publish-ghcr.yml`).
- **production**: namespace `assessment-platform` (never rename it). Changes only
  via the **Promote to production** workflow, and only to an image staging runs.

Rules:

- A setting that differs per environment goes in `k8s/overlays/<env>`, never in
  `k8s/base`. `tests/test_k8s_config.py` holds the overlays, the rollout script's
  namespace map and the lines the deploy rewrites in step.
- Staging uses test data and test accounts only. Never put a production key, URL
  or worker secret in the staging namespace's secret.
- "Deployed" in a verify recipe now means **staging**. Prove a voice change there
  before anyone promotes it.

Trap: **a worker on your laptop can steal staging's sessions.** `new-test-agent`
is also handy for local runs, and LiveKit dispatches by agent name to whichever
registered worker answers first. A local worker left on the default names
(`assessment-self-hosted`, `assistant-self-hosted`) competes with the staging pods.
It takes staging's rooms and posts to your local API, while staging's workers take
yours. Locally, set platform-api's `LIVEKIT_AGENT_NAMESPACE=dev-<you>` and the
matching worker names `LIVEKIT_ASSESSMENT_AGENT_NAME=dev-<you>-assessment-self-hosted`
and `LIVEKIT_ASSISTANT_AGENT_NAME=dev-<you>-assistant-self-hosted`.

## Cutover discipline

New workers register new agent names and take traffic through the backend
routing resolvers. That traffic is **unconditional** — there is no allow-list,
no per-user or per-org gate, and no route back to `livekit/`, so a bad release
is recovered by a production rollback rather than an environment change
(see `k8s/README.md`). Because nothing gates a widening, the parity harness and a
manual smoke of the affected session type belong before the merge, not before a
rollout.

Legacy workers in `livekit/` are never modified to accommodate the new ones.
