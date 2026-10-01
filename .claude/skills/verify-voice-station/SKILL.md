---
name: verify-voice-station
description: How to prove a change to the live voice station works — assessment-platform workers and platform-api's voice, circuit and bootstrap code. Use before calling any voice change done. Lists which level of proof each kind of change needs, and the traps that make a working change look broken.
---

# Verify the voice station

Pick the **lowest level that can see your change**, run it, and report the
command and its output. Green unit tests are not proof for a change that only
shows up in a live room: CI stayed green here while real bugs shipped.

| Your change | Minimum proof |
|---|---|
| Engine, prompts, `modes.py`, boundaries, config tables | Level 1 |
| Worker ↔ backend contract: bootstrap, transcript delivery, tools, dispatch | Level 2 |
| Circuit timing, room lifecycle, anything on exam day | Level 2, with the circuit flow |
| Hosting, `k8s/`, Dockerfile, env, anything only true when deployed | Level 3 (after the person pushes) |
| A voice model or prompt swap | Level 1 + `scripts/model_bench.py` |

## Level 1 — the repo's own tests (seconds)

```bash
cd assessment && poetry run pytest -q        # ~750 tests, ~11s
cd api && poetry run pytest -q -k "voice or livekit or sittings"   # backend side, if touched
```

A change to `CompetencyFramework`, `Rating` or the marking renderer must also
parse what platform-api really sends. From `api`, with
`sys.path.insert(0, "../../assessment/packages")`, build
`schema_builder.framework_payload(...)` for every rubric in
`seeds/platform-starter.json` and `CompetencyFramework.model_validate` it (four
rubrics: rag, range, boolean, range with nullable domains, on 2026-09-30). The
engine's `extra="forbid"` turns any new payload key into a refused framework.

The boundary guards are part of this run (`test_no_consumer_leakage.py`,
`test_*_worker_boundaries.py`, `test_assistant_worker_modes.py`). A failure
there means the change is in the wrong place, not that the guard is wrong.

## Level 2 — the real worker against a local platform-api (minutes)

The e2e test starts the real assessment worker, joins a real LiveKit room,
plays a spoken sentence and asserts the patient answers and the transcript
comes back. It is the only thing that proves the two halves agree.

1. **Services:** `cd api && docker compose up -d`
   (Postgres on **5433**, Redis on **6380**, not the defaults).
2. **Database:** `poetry run alembic upgrade head`, then
   `poetry run python scripts/seed_platform.py` (`make seed-platform` is only a
   dry run). **A migrated database is empty** — skip the seed and
   every attempt is refused `unknown_exam`, which looks like a worker bug.
   The exam must be **published** with a rubric version; a fresh local `sca`
   draft is refused the same way.
3. **API:** start it on **:8002**.
4. **Env:** the seven vars listed at the top of
   `api/tests/e2e/conftest.py`. LiveKit creds,
   `OPENAI_API_KEY` and `DEEPGRAM_API_KEY` are in `assessment/.env`.
   Also set `ASSESSMENT_PLATFORM_PYTHON` to assessment-platform's interpreter
   (`cd assessment && poetry env info --path`)/bin/python — otherwise
   the worker dies on `No module named livekit.agents` and the test only says
   "no turns".
   The test's own vars: `PLATFORM_E2E_BASE_URL`, `PLATFORM_E2E_TOKEN` (mint one
   with `tests.support.tokens.mint_token` for a real user),
   `PLATFORM_E2E_STATION_VERSION_ID` (a **published platform** station whose
   content has `patient_information`), `PLATFORM_E2E_EXAM_CODE` (that station's
   exam, default `sca`), and `WORKER_SECRET` equal to the running API's (start
   the API with it exported; env beats `.env`). `LIVEKIT_E2E_*` are
   assessment-platform's `LIVEKIT_URL`/`LIVEKIT_API_KEY`/`LIVEKIT_API_SECRET`.
5. **Audio:** a 16 kHz mono WAV for `LIVEKIT_E2E_AUDIO_WAV`:
   `say -o t.aiff "I have had chest pain since this morning" && afconvert -f WAVE -d LEI16@16000 -c 1 t.aiff t.wav`
6. **Run:** `cd api && poetry run pytest -m e2e tests/e2e -q`
   `test_dashboard_e2e.py` covers the assistant worker; its second case also
   needs `make worker` running and `WORKER_SECRET` set.
7. **Clean up:** the run needs `livekit` (rtc, the version assessment-platform
   pins) in platform-api's environment; `aiohttp` and `livekit-api` are already
   locked there. Uninstall only `livekit` afterwards.

The test dispatches under a random `e2e-<hex>` agent name, so the deployed K3s
workers never pick it up. It is safe to run against the shared LiveKit project.

**Circuit (exam-day) flow:** join the room **during the reading phase**. Fetch
`POST /api/v1/me/circuits/{id}/join-token` and connect straight after starting
the circuit. The patient is dispatched on the server's clock when reading ends;
if no one has opened the room by then, the dispatch fails and the circuit sits
overdue for ever (two failed exam-day runs, 2026-09-19).

## Level 3 — deployed (after the person pushes)

A push to `main` that touches `assessment/` is the staging deploy: CI
assessment, then `publish-workers.yml` builds the image and rolls out both K3s deployments. There
is no kubectl context on this machine; check the Actions run for the rollout
step, then run one real session of the affected type.

LiveKit Cloud agents (overflow tier) showing `Updating`/offline is usually a
routine worker recycle, not an outage. Check deploy logs instead:
`lk agent logs --id <ID> --log-type deploy`, looking for `registered worker`.
It streams for ever — run it in the background and stop it after ~40s.

## Traps that look like bugs

- `unknown_exam` → the database is not seeded or the exam is not published.
- "no turns" in the e2e test → the worker ran on the wrong interpreter.
- Patient never arrives on exam day → nobody joined during reading.
- `make typecheck` breaks after an e2e run → uninstall the e2e packages.
- The e2e skips with `needs ['OPENAI_API_KEY']` though it is set → an old
  `tests/conftest.py` that blanks it with no `E2E_OPENAI_API_KEY` stash.
- The e2e passes but the attempt is never marked → the station rendered
  degraded ("serving a degraded render" then "not queueing a marking" in the
  API log): its content has no `patient_information` or template layout.
- Model differences under ~1 role breach per consultation at n=3 are judge
  noise. Do not switch a voice model on spec-sheet reasoning; re-run
  `scripts/model_bench.py`.
