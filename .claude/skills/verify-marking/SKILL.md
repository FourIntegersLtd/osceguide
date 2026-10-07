---
name: verify-marking
description: How to prove a change to marking works — platform-api scoring, rubrics, authored exams, the engine's marking prompts and schemas, reviews and result computation. Use before calling any marking change done. Lists the proof each kind of change needs and the traps that make a correct mark look wrong.
---

# Verify marking

Pick the **lowest level that can see your change**, run it, and report the
command and its output.

| Your change | Minimum proof |
|---|---|
| A domain rule, rubric structure, schema builder, outcome computation | Level 1, and show the rule is called from a route or job |
| Marking prompt or output schema (engine or `renderer.py`) | Level 1 (the oracle contract tests are in it) |
| A new or edited authored exam / rubric version | Level 1 + Level 2 on that exam |
| The scoring job, retries, the LLM client | Level 2 |

## Level 1 — tests (~2.5 min, needs the docker services)

```bash
cd api
docker compose up -d            # Postgres :5433, Redis :6380; without them DB tests skip and a pass means nothing
poetry run pytest -q tests/contract \
  tests/unit/test_rubrics_domain.py tests/unit/test_rubric_validation.py \
  tests/unit/test_platform_seed_file.py tests/unit/test_seed_platform_republish.py \
  tests/unit/test_performance_aggregation.py tests/unit/test_results_domain.py \
  tests/unit/test_reviews_domain.py tests/unit/test_cohort_scoring_oracle.py \
  tests/unit/test_exam_prompts.py \
  tests/repository/test_scoring_job.py tests/repository/test_results_append_only.py \
  tests/http/test_rubrics_routes.py tests/http/test_results_routes.py \
  tests/http/test_reviews_routes.py tests/http/test_platform_attempt_routes.py \
  tests/http/test_org_authored_exams.py tests/http/test_attempt_coverage_routes.py \
  tests/unit/test_rubric_authoring.py tests/http/test_rubric_authoring_routes.py \
  tests/http/test_rubric_trial_routes.py
make guards                     # includes test_domain_rules_are_reachable
```

285 passed on 2026-09-25. `tests/contract` holds the oracles
(`test_feedback_model_parity`, `test_engine_schema_parity`,
`test_prompt_rendering`, `test_cohort_scoring_oracle` in unit). A diff against
`tests/fixtures/legacy_*` is a change in what candidates are marked against:
say so in the report, never update the fixture.

The api installs the engine straight from `assessment/packages/osce_assessment`,
so an engine change needs no install step. After one, also run
`cd assessment && poetry run pytest -q`.

A change to the seed, the generator or `seeds/rubric_hints/*.json`: rerun
`PYTHONPATH=. poetry run python scripts/generate_platform_seed.py`, then
`tests/contract/test_rubric_matches_legacy_model.py` must show zero leaf
differences for all 4 exams. Then prove it in the local DB:
`PYTHONPATH=. poetry run python scripts/seed_platform.py --republish` must
report the exam "republished, new version bound", a second run "left
untouched", and each `exams.rubric_version_id` must point at a published
version whose `structure->>'schemaVersion'` is `2`. Parse every
`rubric_versions.structure` through `domain.parse_structure` too: nothing
stored may fail it.
Hand-edit nothing in `seeds/platform-starter.json`: put the decision in the
hints (e.g. `liveDomains`) so `test_the_committed_seed_is_what_the_generator_writes`
stays green. A deploy does not republish; after one, staging needs the
`--republish` run against its database before the new rubric marks anything.

## Level 2 — a real mark in a local database

1. Services, `poetry run alembic upgrade head`, then
   `poetry run python scripts/seed_platform.py` (`make seed-platform` is only a
   dry run). An exam must be **published with a rubric version**, or every
   attempt is refused `unknown_exam`.
2. `make start` (:8002) and `make worker` (the scoring job runs there), with
   `OPENAI_API_KEY` set.
   Start both with `WORKER_SECRET` exported (the e2e must send the same one).
3. Produce a finished attempt on the exam you changed — the voice e2e run
   (`verify-voice-station`, Level 2) makes one end to end. For every exam, run
   it once per exam with `PLATFORM_E2E_EXAM_CODE` and that exam's published
   platform station (content with `patient_information`, or the render is
   degraded and nothing is marked). A new user's free trial allows one attempt
   per exam: use a new candidate for a second round.
4. Wait for `score_attempt ... Success` in the worker log per attempt, then read
   the stored result row and the rendered feedback, not the log line:
   - the payload validates against `schema_builder.derive_result_schema` of the
     rubric frozen on the attempt (`rubrics.service_marking.frozen_scoring_rubric`);
     no `jsonschema` is installed, so walk the subset it uses (type, enum,
     min/max, minItems, required, additionalProperties, anyOf);
   - `GET /api/v1/attempts/{id}/feedback` totals equal `totals_read` of it;
   - the debrief prompt: `service_render.render_debrief` with a stand-in
     attempt (`source_attempt_id`, `user_id`) and read its `<marking>` block;
   - the domains are the exam's own: a narrowed rubric that silently marks
     on the full exam looks like a pass.
   One-off scripts need `PYTHONPATH=.` and `import app.main` first, or the ORM
   fails `NoReferencedTableError` (models register on the app import).

### A trial mark (rubric builder, Stage 4)

A change to preview, copy, the trial stream or the evaluator: prove one real
trial without the worker. A script under `PYTHONPATH=.` that imports
`app.main`, copies the seeded SCA rubric with
`rubrics.service_authoring.copy_rubric(session, None, source_rubric_id=...)`,
then runs `attempts.service_trial.prepare_trial` (a pasted `Doctor:`/`Patient:`
transcript) and iterates `trial_stream(plan, service_trial.trial_evaluator())`.
Expect `connected`, `marking` snapshots, then `marked` with totals per domain
(SCA: 3 domains, about 40 s), and the counts of `attempts` and
`candidate_result_revisions` unchanged; roll the session back afterwards. The
key comes from `OPENAI_API_KEY` in `.env` via settings (the script prints
whether it is set); `E2E_OPENAI_API_KEY` is only the pytest e2e's copy.

`POST /api/v1/platform/attempts/{attempt_id}/rescore` re-queues marking for an
attempt with no result. It keeps an existing result, so it cannot show a new
mark on an already-marked attempt.

## Traps

- A failed scoring job is retried by procrastinate (`attempts.jobs.SCORING_RETRIES`), and only the last
  try writes `failed_reason = scoring_failed`. Prove retry changes with `score_attempt_now(..., last_try=True)`
  in `tests/repository/test_scoring_job.py`; the task's strategy is read from `get_jobs_app().tasks`.

- `unknown_exam` → the database is not seeded or the exam is not published.
- Ortho: nullable `anyOf` domains made narrowed rubrics mark on the full exam,
  with every test green (fixed 2026-09-24). Assert the domain list, not "a result exists".
- The legacy fixtures list `properties` alphabetically; only `required` keeps
  the model's declared order. Order children by `required`, or every field
  looks reordered against the oracle.
- A rubric structure may be version 1 or 2 in the DB. Read it through
  `parse_structure`/`rubrics.service.domain_titles`, never `structure["domains"]`.
- `trainee_id` means two things: circuit slots use `users.id`, result decisions use `trainees.id`.
- Strict structured output fixes shape, not content: a model has written a
  sibling field's name as a list item and repeated a priority. The engine's
  `schemas/tidy.py` drops both before validation (never below `minItems`);
  a stray snake_case line in feedback is model noise, not the renderer.
- The station's "Marking your consultation" modal waits on `/me/events`
  (`attempt`, and `resync` on reconnect) plus a poll that never gives up
  (`web/src/capabilities/station-runner/markingWait.ts`). It used to stop
  after ten polls (~165 s), so a slower marking never showed.
- `test_the_engine_only_needs_pydantic` can fail when its file runs whole
  (import order) and pass when selected by id. It passed in the run above.
- A staging walk (exam mode, 2026-10-06): a circuit's attempt exists only after
  the reading phase, and the candidate's mic in Playwright is Chrome's
  `--use-file-for-fake-audio-capture=<wav>%noloop` (48 kHz 16-bit mono, made
  with `say` + `afconvert`). Start the WAV with a few seconds of silence: the
  first utterances are lost while the patient joins. Marking reaches
  `evaluated` ~50 s after completion. The examiner's own ratings lock on
  submit; the lead's form is page state until "Complete review", so a reload
  loses it.
- Two scales on one result: feedback's `total` is the share of G ratings
  (37.93 for 11G/29), the candidate's released `assessment_score` is the cohort
  scale (domain = majority rating, G 100 / A 66 / R 33, mean of domains: 66).
  Both are right; compare each against its own rule.
