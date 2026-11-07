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
- **A stored rubric structure is version 1, 2 or 3** (3 is the author's scheme, compiled to 2 by `domain.upgrade_structure`; `domain.authoring_form` turns any into 3 for the builder). Never read `structure["domains"]` or
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
- **A rubric's `display` block decides what the candidate sees**: `show` (`overall`, `areaScores`,
  `wentWell`, `workOn`, `quotes`; absent means shown, so old rubrics are unchanged) and `feedbackTone`
  (`supportive|formal|brief`, not `tones`, which colours numbers). Both are frozen into the attempt
  snapshot (`service_marking._snapshot_of`; the tone is added to the prompt there). Hiding is done by
  `feedbackModel` in the web, by field role; the API result payload is NOT redacted, and an examiner
  view passes `showAll`.
- **The console's `marked` is `station_is_marked`**, the same test sitting results use; `has_review`
  alone is not "marked". Reviewers hear an AI mark on their own `attempt` stream because
  `sittings.announcements.attempt_progress` also tells the circuit supervisor and the org admins.

- **Peer marks never feed scoring.** A trainee's marks on someone else's practice turn are shown
  to the supervisor live and to the consulted trainee after release; the delivery gate is
  `has_completed_review` (training only), never a peer mark. A live tick is a `partial` draft that
  merges ratings and keeps notes, and is refused over a completed review (`review_already_completed`).

## What a failure looks like here
- A wrong score with no error: a rule never called, a v1 rubric read as v2, a field silently dropped.
- A result changed in place instead of appended, or shown before it was released.
- A drifting schema or prompt: a payload key the framework refuses, an oracle edited to pass.
- A per-exam branch on an exam code instead of `exams.settings`.
- **Slot review board diff (tab 1)**: the board compares against `section[aria-label="Mark this station"]`, not `main` (main's padding shifts every pixel). The seeded scheme keeps one competency per domain (a domain cannot publish without one; stripping it from the stored structure 500s the review form), so the app draws an "Approach" row the board omits, and every candidate sits on a circuit of their own, so the "Candidate 1 of 8" stepper does not show. `e2e/support/seed-slot-review.ts` writes the admin's completed and the supervisor's draft review by SQL because a signed-off result refuses review writes (`review_locked`).
- **Slot review board, rhythm cost and rating words.** `ratingLabel` writes a rag mark as Green/Amber/Red (the boards' words; an author's own scale keeps its words), so a spec finds the button by `name: "Green"`. Review cards use `reviewCard` (`resultsChrome.ts`, p-6 gap-6) not the shared `boardPad`; the 24/28px rhythm alone moved tab 1 from 21.7% to 32.0% at 1440, because every card is taller than the board's and the offsets compound down the page. Hiding the Approach rows barely helps (31.3% stand-in): a domain's rating is always its own field plus the one competency rating a domain must have to publish, so the rows cannot be collapsed without dropping an input. The seed sets Amara's Communication machine mark to Amber (the fixture gives Green).
- **Board dialogs on the results screens use `PeopleDialog`** (`domains/assess/ui.tsx`: 35.5rem, p-6, h2, lead, Cancel plus commit; Close only when `onCommit` is absent), not the foundation `ConfirmModal` (28rem, icon well, 37 other users). Swapping took release and back-to-draft from 37-86% to 12-14% against the board; the rest is type size in `PeopleDialog`, shared with People, so not tuned here. The preview keeps its by-station list (a feature), so it stays far from the board's short body (57%): a named exception.
- **Decision block (18.2%) is mostly data, not spacing**: spacing is about 9 points; the rest is the seeded Fail vs the board's "Not decided", Reviewed 0 of 6 vs 6 of 6, an enabled Sign off, and "E2E" station titles. Seed to the board's state before blaming CSS.
- **Slot review board states (tabs 2-4).** The board's `.g2` stretches cards to the tallest in a row: hide that with `.g2{align-items:start}` board-side and give the app card the board card's width via `evaluate`. Short state cards (marking, could not be marked, not your circuit) are the board's `.pad` (20px, 14px gap): `stateCard`, not `reviewCard`, with `leading-[1.2]` headings. The admin review card is seeded by SQL into `gp_lead_reviews` (a signed-off result refuses review writes). So a signed-off station answers `review_locked`, never `review_conflict`: force the 409 with `page.route` on the PUT (body is flat `{code, message}`, not `{error:{...}}`). The Reviewers card is structurally different from the board's (agreed chip and per-area ratings vs a verdict per reviewer), so it is informational.
