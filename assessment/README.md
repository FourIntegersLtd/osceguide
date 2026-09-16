# assessment-platform

The OSCE Guide assessment engine, and the LiveKit workers that run it.

One engine, many consumers. B2C practice, B2B training circuits, the BMJ
white-label tenant and a future employer recruitment flow are all consumers of
the same runtime. They differ in configuration and workflow, never in engine
code.

## Why this exists

The platform grew two independent LiveKit workers and two independent
evaluation pipelines that do the same thing: resolve a scenario, run a patient
simulation, capture a transcript, score it against a competency framework. The
architecture review found one legitimate structural difference between them,
namely where a scenario is sourced from. Everything else was duplication.

This project extracts that common engine and rebuilds the worker on top of it.
The existing `livekit/` project stays frozen and keeps serving production until
traffic is moved across consumer by consumer.

## Layout

```
packages/osce_assessment/     the engine — no LiveKit, no LLM SDK, no database
  contracts/models.py         definition, attempt, result, scenario, profile, policy, transcript
  contracts/framework.py      what a competency framework is: domains, competencies, scale
  contracts/ports.py          the six boundaries the engine talks through
  runtime/                    attempt runtime, transcript collector, idempotent delivery, fake adapter
  evaluation/                 the shared evaluator: strict structured output, tool-use fallback, schema check
  schemas/                    marking schemas as JSON data, plus strict/inline transforms and a validator
  prompts/                    prompt text as data, platform defaults per framework, ported formatters
  testing/                    in-memory doubles for every port, and a schema-driven example generator
  catalog.py                  the frameworks the platform publishes (content, not machinery)
  compat/                     migration shims, each with a stated end condition
tests/                        engine tests; tests/e2e/ needs a real LiveKit server
packages/voice_infra/         config-driven LiveKit plumbing: backends by label, speech by role, slots, sentry
packages/livekit_assessment_worker/  the assessment worker (see below)
packages/livekit_assistant_worker/   the assistant worker: help, onboarding, dashboard, consulting doctor
hosting/                      container entry, LiveKit Cloud host, gunicorn supervisor for Railway / K8s
k8s/ Dockerfile railway.toml livekit.*.toml  deployment (one process per worker)
```

## The assistant worker

`livekit_assistant_worker` runs the voice features that are not assessments:
help (FAQ answers, optionally with on-screen guidance through the browser),
onboarding (scene-by-scene coaching), dashboard coaching, and the
consulting-doctor role (`consulting-doctor`; a backend whose records name a
persona maps that name at its own boundary). It never imports the engine's runtime or evaluation
(guarded by `tests/test_assistant_worker_boundaries.py`).

Dispatch metadata is `{"session_id", "backend", "candidate_ref"}`. The worker
fetches `GET /api/worker/assistant-sessions/{session_id}` →
`{"session": {session_id, worker_type, candidate_ref, instructions, greeting?,
gpt_live?, extras}}`. Every text the model is given arrives rendered from the
backend: `instructions` is required for every mode and, for help sessions,
already contains the full FAQ (the model reads every entry itself; there is no
search tool), `greeting` is the opening line (without one the model opens by
itself), and `gpt_live` (`{voice, backend, opening}`) makes speech-to-speech
possible, its `backend` text carrying the same FAQ. The worker holds no FAQ
content and no session prompt of its own. Which content the
backend renders is the backend's decision from the client profile the
frontend declared when it asked for the session (surface, exam, current
route, navigation catalog); the worker sees only the result. Onboarding scene
changes announced by the browser are re-rendered by the backend through
`POST .../assistant-sessions/{session_id}/scene` (`{phase, question,
patientLine}` → `{"instructions"}`). Everything the worker decides per
session type is one row in `livekit_assistant_worker/modes.py` (model tier,
tool budget, transcript, handlers). Help sessions post their transcript once
to `POST .../assistant-sessions/{session_id}/transcript`; GPT-Live help posts
usage to `POST /api/worker/sessions/{session_id}/complete`.

Voice-only FAQ help runs speech-to-speech on GPT-Live when the backend sent
`gpt_live` and an OpenAI key is present (falling back to the pipeline if it
cannot start), with the session cap and idle handling from the legacy worker
as defaults (`GPT_LIVE_MAX_SECONDS`, `GPT_LIVE_HARD_WARNING_SECONDS`,
`GPT_LIVE_IDLE_WARNING_SECONDS`, `GPT_LIVE_IDLE_GRACE_SECONDS` override
them); everything else runs on the pipeline. Run it with
`make dev-assistant`, or `OSCE_LIVEKIT_WORKER=assistant make start`.

## Speech settings

Model ids, voices and the spoken style used by both workers are deployment
settings in `voice_infra.speech.SpeechSettings`: any field can be overridden
with `VOICE_<FIELD>` (for example `VOICE_TUTOR_LLM`, `VOICE_VISION_LLM`,
`VOICE_TTS_STYLE` to name a persona). The defaults name no product.

That is also what makes a model comparison runnable without a deploy, and a
rollback a variable rather than a release: `VOICE_PATIENT_LLM=gpt-4o-mini`
puts the previous model back.

Two settings exist because live voice cannot afford a model that thinks before
it speaks. `VOICE_PATIENT_REASONING_EFFORT` and `VOICE_TUTOR_REASONING_EFFORT`
default to `none` and are sent to any model whose id starts with `gpt-5`. The
plugin sets an effort itself, but only for the ids on its own allow-list, which
does not cover every current model; one it does not recognise is left on the
provider's default, and on a reasoning model that costs seconds before the
first word.

The patient and the tutor are deliberately given different voices and
different spoken styles (`VOICE_DEEPGRAM_FEMALE_VOICE` against
`VOICE_DEEPGRAM_TUTOR_VOICE`, `VOICE_PATIENT_TTS_STYLE` against
`VOICE_TTS_STYLE`). Two roles sharing one voice is the part of role confusion
a listener notices first.

## Choosing a voice model

`scripts/model_bench.py` replays a scripted consultation against several models
and scores how well each one holds its role. It exists because the useful
question is not which model is newest but which is the cheapest one that stays
in character, and that is not answerable from a spec sheet.

```bash
poetry run python scripts/model_bench.py run --arms gpt-4o-mini,gpt-5.4-nano --repeats 3
poetry run python scripts/model_bench.py run --role tutor \
    --script scripts/bench/doctor_debrief_sca.json --arms gpt-4o,gpt-5.4-mini --baseline gpt-4o
```

Every arm gets the same prompt and the same doctor script; only the model
changes. `--instructions-file` and `--reminder` exist for the other kind of
question: holding the model fixed and changing what it is told, which is how
the current prompts were shown to be worth their change. The doctor script contains turns that
deliberately invite a breach, because that is how drift happens in a real
consultation: a candidate asks the patient what they should do, or thinks
aloud, or speaks in a patient's register. Each transcript is then scored by
`claude-opus-5`, chosen from a different model family than anything under test
so that no arm is graded by its own relatives.

The table reports role breaches, time to first token, whole-response latency,
output tokens and cost per consultation computed from the usage the API
reported. Adopt a candidate only when it is no worse on breaches and no more
expensive; on a tie the incumbent stays.

Barge-in and recovery cannot be measured this way. Shortlist with the harness,
then run the top two live with `make dev-assessment` and read the
`[LATENCY:...]` lines the worker already logs.

The current defaults came out of that harness rather than a spec sheet. The
patient stayed on `gpt-4o-mini`: `gpt-5.4-nano` tied on role adherence and
quality while costing 84% more and answering more slowly. The tutor tier moved
from `gpt-4o` to `gpt-5.4-mini`, which held the role better for 76% less.

One caveat on that second change. The tutor tier serves both the debrief and
the consulting-doctor persona, and only the debrief was benchmarked, so the
consulting doctor inherits the new model untested. It is worth a listen before
you rely on it, and `VOICE_TUTOR_LLM=gpt-4o` puts the old model back without a
deploy.

## The assessment worker

`livekit_assessment_worker` runs one attempt's interaction and nothing else.
It knows no product, no station shape, no prompt template and no marking
schema; the import guard in `tests/test_assessment_worker_boundaries.py`
fails if it ever loads one.

What a backend must do to dispatch to it:

1. Register itself in the worker's `VOICE_BACKENDS_JSON` under an opaque label
   (say `practice`), naming the env vars that hold its base URL and worker
   secret, the header that carries the secret, and its cloud-slot routes. A
   backend that mounts its worker routes under a prefix also declares
   `attempt_path`, `transcript_chunks_path` and `transcript_path` (each with
   an `{attempt_id}` placeholder); left out, they default to the paths below.
2. Dispatch with job metadata `{"attempt_id", "backend", "candidate_ref"}`
   (snake_case or camelCase). All three are required: `candidate_ref` is the
   LiveKit identity the candidate will join with.
3. Serve `GET /api/worker/attempts/{attempt_id}` returning
   `{"attempt": AssessmentAttempt, "scenario": Scenario}` where the attempt's
   interaction profile already carries **rendered** instructions and the
   definition omits its `evaluation_policy`. The backend renders; the worker
   receives finished text and is never told how the transcript is scored.
4. Accept `POST /api/worker/attempts/{attempt_id}/transcript-chunks` (one
   `TranscriptMessage` per turn, best effort) and
   `POST /api/worker/attempts/{attempt_id}/transcript` (the completed
   `Transcript`, retried on non-2xx, delivered once). Score it there.

Tools: the profile may name tools (``tools``) and carry the rendered data they
need (``tool_context``); the worker owns the implementations in
`livekit_assessment_worker/tools.py`. Today that is `highlight_lines` for tutor
(debrief) sessions: the model quotes the short line ids from its instructions,
the tool translates them through `tool_context["id_mapping"]` and publishes
`{"transcript_message_ids", "recommendations"}` to the room for the client to
highlight. A profile naming an unknown tool fails the job at start.

Job lifecycle: connect → settle and leave if another agent is present → fetch
the attempt → wait up to 120s for the candidate (exact identity match, or a
substring match when the client appended a suffix and no exact match exists)
→ run the engine's `AttemptRuntime` with the LiveKit adapter (audio pinned to
the candidate, speech stack chosen by the profile's role) → stream and deliver
the transcript. Evaluation is not the worker's job: the runtime stops at
`INTERACTION_COMPLETE` when no evaluator is configured.

Room model the dispatcher must uphold: one agent per room at a time (the
worker leaves if another `agent-*` identity is present, so remove stale agents
before re-dispatching into a shared room); the candidate joins with an
identity equal to `candidate_ref`; any other humans in the room (a supervisor,
observers, candidates waiting their turn) are neither listened to nor
transcribed. Session types, exams and consumers are the backend's business:
the worker sees only an attempt id, a backend label and a candidate.

Run it: `make dev-assessment` locally against `.env`; `make start` in a
container (gunicorn `/health` supervising the worker, `OSCE_LIVEKIT_WORKER`
selects which); LiveKit Cloud via `hosting/livekit_cloud_host.py` and
`livekit.assessment.toml`.

## The three-layer model

An **AssessmentDefinition** says what should be assessed: a scenario reference,
an interaction profile, a competency framework and an evaluation policy. It is
versioned. An **AssessmentAttempt** snapshots a definition and records what
happened when one candidate ran it. An **AssessmentResult** is what the
evaluator concluded, tagged with the policy version that produced it. Editing a
definition tomorrow cannot change what a past attempt was scored against.

A **CompetencyFramework** owns the *shape* of a result: which domains and
competencies exist and what scores may be given. An **EvaluationPolicy** owns
the *scoring*: which model, which prompt, which thresholds, which version. That
split is what lets two consumers mark the same interaction differently, and it
is why shape is data rather than a Python class — a framework can equally
describe a platform exam or one an organisation authored and stored as a row.

The runtime carries a framework id and never looks one up, so the catalogue is
a leaf that only callers use. When org-authored frameworks arrive they come
through a provider, exactly as org-owned scenarios do, and `catalog.py` becomes
one implementation among two.

## The consumer-agnostic rule

The engine never learns who is calling it. Consumer identifiers travel in
`AssessmentAttempt.attempt_context` as opaque strings and come back untouched,
so the runtime cannot branch on them. Consumers keep three decisions:

- which worker a session is dispatched to (backend routing)
- which `EvaluationPolicy` scores the transcript
- where the transcript and result are persisted

`tests/test_no_consumer_leakage.py` enforces this by parsing every engine
module. Legacy exam vocabulary is quarantined in `compat/`, which the engine
itself may not import, and the engine may not import an LLM, transport or
database SDK at all. Prose is exempt: explaining what the engine replaces
carries no coupling.

Two consumers can score the identical interaction differently by passing a
different policy. That is the mechanism that makes an employer assessment and a
B2C practice run the same engine call.

## Development

```bash
make install       # poetry install (Python 3.11)
make test          # poetry run pytest -q
make lint-leakage  # the consumer-agnostic guard on its own
```

End-to-end tests are marked `e2e` and excluded by default; they run only when
`LIVEKIT_E2E_URL`, `LIVEKIT_E2E_KEY` and `LIVEKIT_E2E_SECRET` are set.

## Consuming the engine from the backends

`b2c-api` and `b2b-api` deploy from their own directories, so they vendor the
engine rather than depend on a sibling path.

To pick up an engine change, run this in the consumer, with a clean working
tree and this repo checked out alongside it:

```bash
make engine-sync
```

That is the whole procedure. Nothing needs doing in this repo first.

Under the hood `git subtree` can only pull from a branch whose root *is* the
engine folder, so `engine-sync` generates one from `packages/osce_assessment`,
pulls it, and deletes it again. That branch is a machine-made view: it is never
pushed, reviewed or merged. Merging it would be refused as unrelated history,
and forcing it through would empty the package contents into the repository
root.

The consumer adds `vendor/osce-assessment` to its import path, so
`import osce_assessment` resolves to the vendored copy. Each consumer's CI
validation asserts `osce_assessment.__version__` against its pinned minimum,
so a stale vendor copy fails loudly instead of drifting.

## End-to-end tests and the parity harness

`tests/e2e/` runs the assessment worker against a real LiveKit project and is
skipped unless `LIVEKIT_E2E_URL/KEY/SECRET`, `LIVEKIT_E2E_AUDIO_WAV` (a 16 kHz
mono WAV of one spoken candidate turn) and the speech keys are set:

```sh
poetry run pytest -m e2e tests/e2e -q
```

It starts a stub backend and a worker subprocess, dispatches, joins as the
candidate, plays the audio and checks that turns are streamed, the transcript
is delivered exactly once, a duplicate dispatch leaves one agent, and an
absent candidate delivers nothing.

`scripts/parity_run.py` is the cutover gate: `play` drives a backend-created
room (legacy-routed or assessment-routed) with the same audio; `compare`
normalises the two stored transcripts (legacy b2c, legacy b2b or engine shape),
compares turn and role counts, and with `--evaluate` scores both through the
shared evaluator and compares the result sections.

## Cutover from the legacy `livekit/` workers

Both backends route to the new workers behind allow-lists that default to off;
rollback is emptying the variable. Gate every widening on the parity harness
(`scripts/parity_run.py compare --evaluate` against a legacy transcript of the
same type) and a manual smoke of that session type.

1. B2C conversations: `LIVEKIT_B2C_ASSESSMENT_WORKER_TYPES=conversation,admin-test`
   with `LIVEKIT_B2C_ASSESSMENT_USER_ALLOWLIST=<a few emails>`, then `*`.
2. B2C debriefs: add `debrief` to the same list once conversations are stable;
   confirm the highlighted lines and recommendations render in the debrief screen.
3. B2C assistant sessions: `LIVEKIT_B2C_ASSISTANT_WORKER_TYPES=help`, then
   `help,onboarding,dashboard,athena-doctor`; allow-list a few users, then `*`.
4. B2B: `LIVEKIT_B2B_ASSESSMENT_ORG_SLUGS=<pilot org>`, then `*`.
5. Retire legacy: stop the Railway `livekit-b2c` / `livekit-b2b` services, delete
   the Cloud agents in `livekit/livekit.b2c.toml` and `livekit.b2b.toml`, and
   mark `livekit/` archived in the root `AGENTS.md`.

Differences from the legacy workers to keep in mind:

- The agent ends the interaction and leaves when the candidate disconnects; a
  candidate who refreshes mid-session starts a new session (B2B re-dispatches on
  every turn switch already).
- Only assessment sessions stream per-turn chunks; help posts its transcript
  once at the end. Help answers come from the FAQ rendered into the
  instructions; there is no FAQ search tool.
- The assessment worker waits up to 120s for the candidate
  (`LIVEKIT_ASSESSMENT_CANDIDATE_TIMEOUT_S`); the assistant worker 30s.
- B2C assessment sessions default to the self-hosted agent
  (`LIVEKIT_B2C_ASSESSMENT_ROUTING_MODE=self-hosted`); self-hosted capacity is
  `replicas` × `LIVEKIT_*_MAX_CONCURRENT_JOBS` (default 8). To get the legacy
  Cloud-first behaviour, deploy this worker to LiveKit Cloud as
  `assessment-livekit-cloud` (`lk agent create --config livekit.assessment.toml`
  with `OSCE_LIVEKIT_HOSTING=cloud` and that agent name in the secrets file,
  then fill in the toml) and set the mode to `livekit-cloud`: b2c-api then
  reserves a slot in the shared `LIVEKIT_CLOUD_MAX_CONCURRENT` pool and, when it
  is full, overflows to `assessment-self-hosted`. The assistant worker still
  dispatches only to `assistant-self-hosted`.
- The `recommendation` and `vision` session types were removed from the product
  rather than ported.

Deployment: `.github/workflows/publish-ghcr.yml` builds
`ghcr.io/fourintegersltd/osceguide-assessment-platform` after CI on `main` and,
with the `K8S_AUTO_DEPLOY` repository variable set, pins the digest into both
`k8s/deployment*.yaml` and rolls them out through
`scripts/k8s_rollout_on_control_plane.sh`. Both backends must vendor an engine
that carries `AIInteractionProfile.tool_context` (refresh with `make
engine-sync` in the consumer).
