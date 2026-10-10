---
paths:
  - "api/app/features/{attempts,voice}/**"
  - "api/app/features/*/router_worker.py"
  - "api/tests/e2e/**"
  - "assessment/**"
  - "web/src/foundation/livekit/**"
  - "web/src/capabilities/{attempt-runner,station-runner,feedback,debrief,transcripts,pending-feedback}/**"
---
# Attempt engine: what to know

Owner: `attempt-engine-owner`. Proof: `verify-attempt-engine`. The attempt is the
consultation; scoring (evaluator, jobs, renderer) is `marking-owner`'s. If the bug is in the
mark, hand it back. If the transcript is wrong, the mark is not the bug.

## Boundaries (test-enforced; never weaken a guard to pass)
- The engine (`packages/osce_assessment`) is consumer-agnostic: no B2C, B2B, tenant, employer
  or organisation awareness; consumer ids pass through `attempt_context` as opaque strings.
  `tests/test_no_consumer_leakage.py`. Legacy vocabulary (`app_type`, `sca`/`plab`/`casc`/`ortho`)
  lives only in `compat/`.
- `livekit_assessment_worker` (patient and debrief) must not import `osce_assessment.prompts`,
  `.schemas`, `.catalog`, `.evaluation`, `.compat`, nor name a product, station field or storage
  system. It receives rendered instructions from the backend's bootstrap route and delivers
  transcripts back; scoring happens backend-side. Its tools are named in the profile (`tools`)
  with data in `tool_context`; implementations are in `tools.py` and stay about transcripts and
  the room. Guard: `test_assessment_worker_boundaries.py`.
- `voice_infra` takes a `BackendEndpoints` value, never a product string. Model ids, voices and
  style are `SpeechSettings` (`VOICE_<FIELD>` env); never hardcode a model or persona. Reasoning
  effort defaults to `none`. LiveKit pins match `livekit/pyproject.toml` exactly.
- `hosting/` runs one worker per process (`OSCE_LIVEKIT_WORKER`); add new workers to
  `hosting/workers.py`. Never put a shell, make or supervisor in front of it: the stop signal
  must reach the LiveKit SDK or a terminating pod keeps taking sessions.
- Every live persona opens by naming the role it is cast in (`prompts/_blocks`;
  `test_prompt_role_locks.py`). Do not re-send a role reminder every turn: measured worse.
  Greetings come from `prompts/greetings.py`.

## Debrief
- The tutor walks the management plan together (PEARLS, not Pendleton) and may play the patient
  once; only the role lock's `exception` line allows that. Change the debrief prompt only after
  `scripts/debrief_bench.py` against the baseline (about $2 for 16 debriefs).
- Ten-minute clock: `prompts/debrief_pacing` writes the plan, platform-api sends it as
  `tool_context["pacing"]` with `check_time` in `tools`; `voice_infra.pacing` holds the clock.
- Cloud vs self-hosted voice stacks: `speech.py` builders branch on `cloud_hosting.is_livekit_cloud()`
  (the one reader of `OSCE_LIVEKIT_HOSTING`). Cloud uses `livekit.agents.inference`, which needs
  `LIVEKIT_API_KEY`/`LIVEKIT_API_SECRET` at construction (tests set them); self-hosted keeps the
  direct plugins and provider keys, unchanged.
- Swapping a voice model: re-run `scripts/model_bench.py`; under ~1 role breach per consultation
  at n=3 is judge noise.

## Backend
- Every attempt is refused `unknown_exam` until the DB is seeded and the exam is published with
  a rubric version. It looks like a worker bug.
- A station with no `patient_information` (or template layout) renders degraded, is never frozen,
  and its attempt is silently never marked. Check the stored result, not the e2e.
- Circuit rooms: join during the reading phase; the patient is dispatched on the server's clock
  (ADR 0018). The worker contract is `/api/worker/*` (`router_worker.py`, secret-guarded).
- The evaluator runs the engine in a thread; a cancelled caller cannot stop it.
- After an engine change run `poetry install` in `api`: it holds a copy (`develop = false`).
- Removing e2e leftovers: delete users before stations (`station_versions` is RESTRICT).

## Deploys and laptops
- Push to `main` touching `assessment/` deploys staging (K3s, namespace
  `assessment-platform-staging`); production only via "Promote workers to production"
  (ask first). Per-environment settings live in `k8s/overlays/<env>`, never `k8s/base`.
  Staging uses test data only. "Deployed" means staging.
- **A local worker on the default names steals staging's sessions.** Locally set
  `LIVEKIT_AGENT_NAMESPACE=dev-<you>` and worker names `dev-<you>-assessment-self-hosted` /
  `dev-<you>-assistant-self-hosted`.
- New workers take traffic unconditionally; the parity harness and a manual smoke come before merge.
- `livekit/` is frozen: never edit or push.
