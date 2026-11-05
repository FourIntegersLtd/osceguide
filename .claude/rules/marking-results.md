---
paths:
  - "api/app/features/{rubrics,catalog,results,reviews}/**"
  - "api/app/features/attempts/{evaluator,jobs,jobs_coverage,llm_clients,renderer,service_render,router_coverage,service_coverage}.py"
  - "api/tests/contract/**"
  - "assessment/packages/osce_assessment/{evaluation,schemas,prompts}/**"
  - "web/src/capabilities/feedback/**"
  - "web/src/domains/assess/results/**"
---
# Marking and results: what to know

Owner: `marking-owner`. Proof: `verify-marking`. The decision and review workflow and its screens
are `institution-owner`'s; this is how a mark and an outcome are computed.

- Exams and rubrics are authored data (ADR 0016); an exam has an owner (ADR 0017). Per-exam
  behaviour lives in `exams.settings` (`catalog.schemas.ExamSettings`). **Never branch on an exam
  code** (`test_no_exam_code_branches.py`). B2B defines its own exams.
- **A stored rubric structure is version 1 or 2.** Never read `structure["domains"]` or
  `["scale"]`: use `rubrics.service.domain_titles` or `rubrics.domain.parse_structure`, which
  upgrade v1 on read. The dashboard did, and a republished v2 rubric would have emptied it.
- **A rubric draft may be invalid.** Create and edit save any structure; only publish refuses.
  Read a version's `problems` before treating a draft as markable (`service_marking.trial_rubric`).
- **A stored result payload is the marks alone**, validated by the rubric's derived schema
  (`additionalProperties: false`). The model is the row's `model_used` column.
- Rubric arithmetic is `rubrics.service_scoring`. A rule that passes its unit test but is never
  called is not done: 20 domain rules shipped that way (`test_domain_rules_are_reachable`).
- Results are append-only (`tests/repository/test_results_append_only.py`).
- Oracles: `tests/fixtures/legacy_schemas/`, `legacy_prompts/` and the contract tests that read
  them. **Never edit an oracle to make a test pass.** To stop asking for a legacy field, list its
  dotted path under `omit` in `seeds/rubric_hints/<exam>.json` (and rename a section with
  `titles`), then regenerate: the contract test drops `omit` paths from the oracle and refuses
  one the oracle lacks. A stored mark keeps the rubric frozen on its attempt, so old marks render
  their old fields (SCA dropped its per-domain summaries and language notes 2026-10-11).
- The engine (`assessment/`) takes a framework id and `CompetencyFramework`; scoring concerns
  (model, prompt, thresholds) never go on a framework, result shape never on an `EvaluationPolicy`.
  `extra="forbid"` turns a new payload key into a refused framework: after changing
  `CompetencyFramework`, `Rating` or the renderer, validate `schema_builder.framework_payload` for
  every rubric in `seeds/platform-starter.json`.
- The debrief's marking block is one walk by role (`prompts/debrief_feedback.py`
  `render_marking`): fields placed by `field_roles` (`contracts/rating.py::FieldRole`), ratings
  worded by `_rating_text.rating_text`. Never add a per-exam formatter or read a field by name; a
  v1 framework with no `field_roles` still renders every field as `other`. Fixtures:
  `assessment/tests/fixtures/frameworks/`.
- Web: feedback and review forms are drawn from the rubric (`capabilities/feedback/rubric.ts`,
  `domains/assess/results/reviewForm.ts`). A rating is coloured by its position in the scale,
  not its letter.
- Changing scoring for an existing consumer is ask-first. See `docs/ATTEMPT-LIFECYCLE.md`.
- Swapping the marking model: measure first with `assessment/scripts/marking_bench.py` (staging
  attempts only); a candidate must stay within the incumbent's own run-to-run noise. 2026-10-24:
  every newer OpenAI model (gpt-6-luna, gpt-5.6-luna/terra) agreed with the others but marked
  harsher than gpt-5-mini. Owner decision 2026-10-31: marking_primary_model is gpt-6-luna now
  (gpt-5-mini shuts down 2026-12-11), harsher marks accepted, no re-bench. Effort `low` passes
  straight through as `reasoning_effort` (no allow-list). Railway may still set MARKING_PRIMARY_MODEL.
- `MARKING_PRIMARY_PROVIDER` (`openai` default | `anthropic`, anything else refuses to boot) is
  `EvaluationPolicy.first_provider`: it orders the two slots for scoring and live coverage
  (`providers.ordered_slots`). `openai_*` is always the OpenAI slot and `anthropic_*` the Anthropic
  one (the `primary_client`/`fallback_client` factories keep their names); a missing key falls through to the other. `provider`/`fallback_used` mean "first/second asked";
  `model` is the model that actually marked. Marks as Anthropic-first are not benched (see below).
- The Anthropic path (claude-sonnet-5-5, `anthropic_call.ask_by_tool`) sends no `temperature` and no
  forced `tool_choice` (400 on either); the prompt asks for the tool. Structured outputs
  (`output_config.format`, or strict tools) were measured 2026-10-31 with a strict, inlined schema,
  `minItems` clamped: all 4 seeded rubrics (19-70KB) answer 400 "compiled grammar is too large", and so
  do any two ~6.5KB PLAB domains together. Do not retry whole-rubric schemas. Its thinking counts
  against `anthropic_max_tokens` (16000; 7500 truncated 7 of 16). A reply off the schema is answered in
  the same conversation with its own errors (`tool_result`, `is_error`), up to twice; the system
  prompt carries `cache_control`.

- **Scoring holds no DB line during the model call** (`jobs.py`): `prepare_scoring` (short session) ->
  `evaluator.evaluate` (none open) -> `record_scoring` (new session, re-checks `should_score` and
  MARKABLE). `score_attempt_now` takes a session *opener*, not a session; `PreparedScoring` carries
  plain values, never ORM rows. Jobs queue with `lock=score:<attempt>` and `priority=10`; retry is
  `max_attempts=4, exponential_wait=8`. Clients take `marking_llm_timeout_seconds`/`_max_retries`, the
  engine's per-request `timeout_s` defaults to 180 (a per-request value overrides the client's), and
  markings run on `evaluator._marking_pool()` (`worker_concurrency` threads), not `asyncio.to_thread`.
  `save_result` may return a bool (C1.3): `False` means another run stored it, so do nothing more.

## What a failure looks like here
- A wrong score with no error: a rule never called, a v1 rubric read as v2, a field silently dropped.
- A result changed in place instead of appended, or shown before it was released.
- A drifting schema or prompt: a payload key the framework refuses, an oracle edited to pass.
- A per-exam branch on an exam code instead of `exams.settings`.
