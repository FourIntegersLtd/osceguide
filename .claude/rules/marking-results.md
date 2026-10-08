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
  them. **Never edit an oracle to make a test pass.**
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
