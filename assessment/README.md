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
```

Packages still to land: `voice_infra` (config-driven port of `livekit_voice`),
`livekit_assessment_worker` (patient and debrief interactions),
`livekit_assistant_worker` (help, onboarding, dashboard, athena-doctor).

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
engine rather than depend on a sibling path. The `engine` branch of this repo
is the contents of `packages/osce_assessment` as a standalone history; refresh
it with `make engine-branch` after any engine change consumers should see.

First time, in a consumer with a clean working tree:

```bash
git subtree add --prefix vendor/osce-assessment/osce_assessment \
    ../assessment-platform engine --squash
```

Later updates:

```bash
git subtree pull --prefix vendor/osce-assessment/osce_assessment \
    ../assessment-platform engine --squash
```

The consumer adds `vendor/osce-assessment` to its import path, so
`import osce_assessment` resolves to the vendored copy. Each consumer's CI
validation asserts `osce_assessment.__version__` against its pinned minimum,
so a stale vendor copy fails loudly instead of drifting.
