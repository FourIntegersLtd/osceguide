# assessment-platform — AGENTS.md

Instructions for AI coding agents working in this project. The root
`OSCE Guide/AGENTS.md` still applies; this file adds the rules for this subtree.

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
session-prompt module reappearing). Instructions, greetings, the FAQ corpus
and speech-to-speech instructions all arrive rendered in the bootstrap; the
templates live in `backend/b2c-api/b2c/shared/services/assistant_prompts/`
and the content they render (FAQ packs per exam and surface, greetings,
persona, onboarding scenes) in `.../assistant_content/`, selected by the
client profile the frontend declares (surface, current route, navigation
catalog). The worker never sees a navigation label, a product name or an
exam id (`tests/test_assistant_worker_no_product_vocabulary.py`).
The UI-guidance toolset is a port of the legacy worker's; keep it in step
with the frontend `livekit-ui-guidance` package.

Model ids, voices and spoken style are `voice_infra.speech.SpeechSettings`
(`VOICE_<FIELD>` env). Do not hardcode a model or a persona name in a worker.

`hosting/` runs one worker per process, selected by `OSCE_LIVEKIT_WORKER`;
add a worker to `hosting/workers.py` when it lands.

The LiveKit pins must match `livekit/pyproject.toml` exactly, including the
documented `anthropic >=0.41,<1.0.0` httpx constraint.

## Cutover discipline

New workers register new agent names and take traffic through the backend
routing resolvers behind an allow-list. Legacy workers are never modified to
accommodate the new ones. Every widening is gated on the parity harness.
