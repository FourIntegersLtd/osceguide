# Plan: Rubrics as templates — one model for marking, feedback and dashboards

> **Status: built.** All four stages landed on 2026-09-30. This file is kept as the record of
> the design and why it was chosen. Paths in it are from before the move to one repository
> (`backend/platform-api/` is now `api/`). What is still owed is in `web/docs/BACKLOG.md`
> (R-1, R-4, R-5, R-8); add nothing new here.
>
> Supersedes the earlier draft of this file (all of its content is carried here). A standalone plan
> to build on: 4 stages, each shippable on its own.

---

## 1. Context

**The problem.** A rubric today is `domains → competencies`, and the fields every competency answers
are hard-coded in `backend/platform-api/app/features/rubrics/schema_builder.py::_scored_property`: an
R/A/G `score`, a `supporting_phrase`, a `score_explanation`. As a result:

- **The marker is told the wrong shape for 3 of the 4 platform exams.** PLAB 2 scores 0..1 with
  `completed/missed/critical_flags/suggested_actions`. CASC is a `competent` yes/no with
  `generic_domains` per domain. Ortho is 0..10 with `score_justification/evidence_points`, nullable
  domains and a `station_type`.
- **SCA's written sections fit only through an escape hatch.** `clinical_analysis` and
  `actionable_feedback` go through `SectionSpec(kind="object")`, which carries a raw schema.
- **Candidate feedback is hand-written per exam in platform-web.** It lives in
  `src/capabilities/feedback/exams/*`, while `model.ts` is R/A/G-only.
- **The dashboard's scoring is hard-coded per exam** in `src/domains/train/dashboard/examConfig.ts`.
- **Institution screens assume every exam is R/A/G.** The cohort ranking, sitting report, CSV and
  readout all score through `reviews/scoring.py::RAG_SCORES` (G100/A66/R33).
- **The rubric editor is raw JSON** (`platform-web/src/capabilities/authoring/sections/RubricDetail.tsx`).

**The owner's requirements.**

1. **A rubric is a template, like a station template.** Sections hold fields. Each field has a label,
   an answer format, a required flag and draft instructions that start from the exam model and can be
   edited per rubric.
2. **Exact match.** The 4 platform rubrics match their legacy b2c feedback models exactly, every field.
3. **The marker respects the rubric.** It produces exactly the fields the rubric defines.
4. **Native scoring.** No exam is forced onto R/A/G.
5. **Faithful display.** Candidate feedback and the dashboard are drawn from the rubric and look as
   b2c shows them today.
6. **No hardcoding.** An exam is data. Adding an exam means writing a rubric, not code.
7. **Institution parity.** Institutions can fully customise stations, marking, feedback and
   dashboards themselves, with no engineering.

**Already in place, so we build on it.**

- **The engine already rates natively.**
  `assessment-platform/packages/osce_assessment/contracts/framework.py` has
  `Rating(kind: rag|scale|range|boolean, minimum, maximum, step)`, `rating_field`, nullable-domain
  handling in `scores_in`, `domain.competency` qualified ids, and native `validate_scores`. platform-api
  just never sends a rating (`schema_builder.framework_payload` sends only `scale`).
- **Institutions already own authoring.**
  - Org admins create, edit and publish rubrics (`rubrics/router_org.py`) and station templates
    (`stations/router_templates.py`).
  - Platform admins do the same for platform rubrics (`rubrics/router.py`) and templates
    (`stations/router_platform_templates.py`).
- **Rubric versions are immutable once published.** An attempt freezes its rubric in
  `attempts/domain_definition.py` (`evaluation_policy.rubric`).
- **The station-template builder exists and is reusable.** It lives in `platform-web/src/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/`:
  - `StructureBuilder`, `SectionFilmstrip`, `SectionStage`, `CanvasBlock` and `AddFieldMenu`;
  - `inspector/BlockInspector.tsx`, which covers answer format, role, required and draft instructions;
  - the helpers `structureBuilderOps.ts`, `blockRoles.ts` and `blockTypeLabels.ts`.
- **A legacy parity oracle exists.** `tests/contract/test_feedback_model_parity.py` provides
  `METADATA_FIELDS`, `marking_content`, `reachable_defs` and `leaf_differences`. The legacy schemas are in
  `tests/fixtures/legacy_schemas/b2c/{sca,plab,casc,ortho}.json`.
- **Uncommitted work to fold in.** In platform-api, `guidance` on domains and competencies,
  `split_description` in `scripts/generate_platform_seed.py`, and `seed_platform.py --fill/--env`. It is
  applied locally only; staging and production are untouched.

---

## 2. Principles (each one changes a decision below)

- **An exam is data.** No code outside the seed generator may branch on an exam code. The proof is the
  "fifth exam" test (§9).
- **One derivation.** The result schema, the engine framework, the examiner form, the feedback view
  and the dashboard maths all come from one parsed rubric. The only exception is legacy-b2c attempt
  rows, which are stored verbatim.
- **A closed vocabulary, not a formula language.** Field types, roles, aggregates and pass rules are
  fixed lists. Institutions pick from options, so nothing they author can be a bug.
- **Refuse bad rubrics at publish, in plain words.** Never fail during a candidate's exam.
- **Migrate callers, then delete.** The per-exam readers, `RAG_SCORES` and the `examConfig` scoring
  go in the same stage that replaces them. No shims.
- **SSE, never polling**, for trial marking.
- **Server-side maths.** Aggregates and pass/fail are computed in platform-api and served. platform-web
  only draws them.

---

## 3. The rubric model (structure `schemaVersion: 2`)

### 3.1 Shape

```jsonc
{
  "schemaVersion": 2,
  "rating": {                          // how one competency is rated — maps 1:1 to engine Rating
    "kind": "rag" | "scale" | "range" | "boolean",
    "field": "score",                  // which competency field holds the rating (CASC: "competent")
    "scale": ["G","A","R"],            // rag/scale only, best first
    "minimum": 0, "maximum": 10,       // range only
    "step": "integer" | "number"       // range only
  },
  "sections": [
    {
      "id": "data_gathering", "title": "Data gathering", "kind": "domain",
      "instructions": "…",             // was `guidance`; what this domain assesses
      "live": false,                   // can be judged mid-consultation
      "nullable": false,               // Ortho: only the station's domains are filled
      "competencies": [
        { "id": "history_taking", "label": "History taking",
          "instructions": "…",         // what the marker looks for
          "descriptors": { "G": "…", "A": "…", "R": "…" } }   // optional anchors per rating value
      ],
      "competencyFields": [ Field, … ],  // what EVERY competency in this section answers
      "fields": [ Field, … ]             // answered once for the domain (CASC generic_domains)
    },
    { "id": "clinical_analysis", "title": "Clinical analysis", "kind": "section",
      "fields": [ Field, … ] }           // written, not scored (SCA narrative, Ortho station_type)
  ],
  "display": Display                     // §4 — feedback + dashboard, all optional
}
```

### 3.2 Field

```jsonc
{ "id": "missed", "label": "Missed", "type": "list", "required": true, "nullable": false,
  "role": "improvement", "instructions": "…",
  // type-specific:
  "options": ["…"],                    // singleSelect
  "fields": [Field…],                  // group (nested object) and records (list of objects)
  "items": "string"                    // list (strings only; list of objects = records)
}
```

- **Types.** The station vocabulary, cut down to what a result can hold:

  | Type | JSON Schema it becomes |
  |---|---|
  | `rating` | The rubric's rating: enum, number or integer with bounds, or boolean. Only in `competencyFields`, exactly once, with id = `rating.field`. |
  | `shortText`, `longText` | string |
  | `list` | array of string |
  | `singleSelect` | string enum |
  | `group` | object with nested `fields` |
  | `records` | array of objects with `fields` |

- **Roles.** A closed list, read by the feedback renderer, the dashboard, the debrief tutor and tutor
  memory. Nothing downstream reads field ids.

  | Role | Meaning / used by |
  |---|---|
  | `rating` | The score |
  | `evidence` | Quotes and evidence points |
  | `explanation` | Why the score |
  | `strength` | What went well |
  | `improvement` | Missed items and issues |
  | `action` | Suggested actions |
  | `flag` | Critical flags; counted as critical on the dashboard |
  | `summary` | Overall narrative |
  | `selector` | Ortho `station_type`; which domains apply |
  | `other` | Anything else |

- **`source: "marker" | "system"`**, default `marker`. A `system` field (e.g. SCA `live_coverage`, if Stage 1
  confirms the live pipeline writes it) is part of the result shape but is not asked of the marker.

### 3.3 Backend code (platform-api `app/features/rubrics/`)

- **`structure.py`:** replace `DomainSpec`/`SectionSpec`/`CompetencySpec` with `RatingSpec`, `FieldSpec`,
  `CompetencySpec(id, label, instructions, descriptors)`, `SectionSpec(id, title, kind, instructions, live,
  nullable, competencies, competency_fields, fields)`, `DisplaySpec` and
  `RubricStructure(rating, sections, display)`.
  - Keep the `.competencies` and `.domains` convenience properties so `scoring_domain_ids`,
    `narrow_structure` and `reviewable_domains` keep working.
- **`domain.py`:**
  - `parse_structure` parses v2 with `_identifier` checks.
  - Add `upgrade_structure(raw)`, which turns v1 (`scale`, `domains`, `sections`) into v2. It maps
    `rating.kind` to `rag` if the scale is G/A/R, else `scale`. It adds the three implied competency
    fields `score` (rating), `supporting_phrase` (evidence) and `score_explanation` (explanation), maps
    `guidance` to `instructions`, and maps a v1 `object` section to a `group` field via
    `field_from_schema` (§5.1).
  - It is called on every read, so existing org rubrics and frozen attempts stay valid. **No DB migration.**
- **New `validation.py`**, modelled on `stations/station_validator.py`. It returns a list of
  `{path, message}` in plain language, and every item blocks publishing:
  - ids are unique per level and are valid identifiers;
  - exactly one `rating` field per domain, with id = `rating.field`;
  - `range` has minimum < maximum; `scale` is non-empty; descriptor keys are on the scale;
  - `singleSelect` has ≥1 option; `group` and `records` have ≥1 field;
  - every scoring domain has ≥1 competency;
  - `display` references only existing ids, and its thresholds sit inside the rating range;
  - **size limits** (constants in one place, set from the provider's documented structured-output limits
    and measured cost in Stage 2):
    - nesting depth ≤ provider max;
    - total properties ≤ provider max;
    - enum values and total name length ≤ provider max;
    - estimated leaf answers (competencies × competency fields + fields) ≤ `MAX_MARKED_LEAVES`.
      The message says how many to remove.
- **`schema_builder.py`:**
  - `derive_result_schema` walks the tree: a domain becomes an object (nullable becomes
    `anyOf:[object, null]`), a competency becomes an object of its `competencyFields`, and domain
    `fields` sit beside the competencies. Each field's `instructions` becomes its `description`.
  - The competency description stays as it is today: label, then anchors, then instructions.
  - `required` follows the field's `required`, and `nullable` becomes `anyOf` with null.
  - `system`-source fields are excluded from the marker schema but included in
    `display_schema` (a second output, used for validation of stored rows).
  - `_scored_property` is deleted.
  - `framework_payload` now also sends `rating` (kind, bounds, step) and `rating_field`, plus nullable
    flags on domains.
- **`result_schema_override` is deleted.** v2 can express every legacy model, and a second way to
  define a shape is the hardcoding we're removing. It is currently used only by seeds; confirm with
  `grep` in Stage 1. Approved (§12): delete it in Stage 1 once the §5.2 contract test is green,
  migrating its callers in the same change.
- **`schemas.py`:** add the v2 structure, `display`, validation errors (`422` with the error list) and
  the resolved display on reads.

---

## 4. Display: feedback and dashboard live in the rubric

### 4.1 Shape (every key optional; defaults in §4.2)

```jsonc
"display": {
  "domain": {
    "aggregate": "ragCounts" | "sum" | "mean" | "percentAchieved",
    "passAtLeast": 2                         // line on each domain bar; in the aggregate's units
  },
  "total": {
    "aggregate": "ragShare" | "sum" | "mean" | "percentAchieved",
    "max": 12,                               // omitted → derived (§4.2)
    "passAtLeast": 7,
    "requireEveryDomain": true               // pass also needs every domain ≥ domain.passAtLeast
  },
  "tones": [ { "atLeast": 0.8, "tone": "good" }, { "atLeast": 0.6, "tone": "fair" },
             { "atLeast": 0, "tone": "poor" } ],   // on the rating as a fraction of its max
  "bands": [ { "from": 43, "to": 50, "label": "…", "tone": "excellent" }, … ],  // named total bands
  "labels": { "domainSubtitle": "Average score out of 4", "totalTitle": "…", "passLabel": "…" }
}
```

- **Tones** are a closed set: `excellent | good | fair | weak | poor`. platform-web maps them to design
  tokens: gray ink, no black (memory `no-black-borders-or-black-text`).
- **An R/A/G rating's tone comes from its scale position**, not from `tones`.

### 4.2 Defaults (one function: `rubrics/domain.py::resolved_display(structure)`)

| Rating kind | domain.aggregate | total.aggregate | total.max | Tones |
|---|---|---|---|---|
| `rag` / `scale` | `ragCounts` | `ragShare` | — | by scale position |
| `range` | `sum` | `sum` | rating max × competencies in the answered domains | 0.8 / 0.6 of max |
| `boolean` | `percentAchieved` | `percentAchieved` | 100 | 80% / 60% |

- **Pass line.** No pass line unless `passAtLeast` is set.
- **Nullable domains** (Ortho) are left out of both the aggregates and `max` when null. This is how Ortho's
  single answered domain gives a total out of 50 with no Ortho code.
- **One function, everywhere.** `resolved_display` is the only place defaults exist. Every read of a rubric
  (API, frozen attempt, performance payload) serves the resolved display.

### 4.3 The four platform exams (checked against `frontend/src/b2c` on 2026-09-30)

Rule: follow what b2c's code computes, not what its copy claims.

| | SCA | PLAB 2 | CASC | Ortho |
|---|---|---|---|---|
| rating | rag G/A/R, field `score` | range 0..1 number, field `score` | boolean, field `competent` | range 0..10 integer, field `score` |
| domain | ragCounts, stacked percent, no pass line | sum /4, line 2 "Min threshold" | percentAchieved, line 80 "Pass threshold" | mean /10, line 7 "Good (7/10)" |
| total | ragShare (headline = G share), no pass, no trend pass line | sum /12, pass ≥ 7 "Pass (7/12)"; requireEveryDomain per legacy `passed_station` (b2c's frontend only reads it from the API; confirm in Stage 1 from legacy backend source, else false) | percentAchieved across all competencies, pass ≥ 80 "Pass (80%)", **no** requireEveryDomain (`CascFeedback.tsx:292-294`) | sum /50 (derived), pass ≥ 35 "Pass (35/50)" |
| tones | scale (G Competent, A Developing, R Development) | ≥.8 good, ≥.6 fair, else poor (per 0..1 competency score) | — (tick / cross; total ≥80 good, else poor) | ≥9 excellent, ≥7 good, ≥4 fair, else poor |
| bands | — | — | — | 0–17 poor, 18–34 fair, 35–42 good, 43–50 excellent; **no text labels** (b2c shows coloured dots only) |
| labels | title "Where you stand"; domain subtitle "RAG mix by clinical domain" (`ScaDashboard.tsx:687`; `examConfig.ts:251` is wrong); trend subtitle "How your skills moved across recent sessions" | domain "Average score out of 4"; trend "Station score over time" | domain "Competency rate by domain"; trend "Competency over time" | domain "Scores by station type or domain"; trend "Station score over time" |

---

## 5. The four platform rubrics, generated from the legacy models

### 5.1 One generic converter (`scripts/generate_platform_seed.py`, rewritten)

**`rubric_from_model(schema, exam_hints)`** takes a legacy JSON Schema and returns a v2 structure.

Generic rules, with no per-exam code:

- A root property whose object's properties all `$ref` the same competency model becomes a
  `domain` section. The competency model's properties become `competencyFields`. Any non-competency
  sibling becomes a domain `field` (CASC `generic_domains` → `group`).
- A root property that is an object of other shapes becomes a `section` of fields (`group`/`records`
  recursively). A root enum becomes `singleSelect` (Ortho `station_type`).
- `anyOf` with null becomes `nullable`.
- Type mapping: `string` → shortText/longText (longText if the description asks for an explanation or
  the name ends in `_explanation` / `_justification`), `array<string>` → `list`,
  `array<object>` → `records`, `enum` → singleSelect, `number` / `integer` with bounds → the rating
  when the name matches the competency model's rating field.
- Descriptions become `instructions`. The existing `split_description` keeps pulling `R:/A:/G:` anchors
  into `descriptors`.

**`field_from_schema`** is the same recursion, reused by `upgrade_structure` for v1 object sections.

**`exam_hints`** is the only per-exam input, a small JSON per exam in `seeds/rubric_hints/<exam>.json`:
- `rating.field`;
- a role per field id, where the name alone is ambiguous;
- `display` (§4.3);
- which `system` fields exist.

This is data, not code.

**Output:** `seeds/platform-starter.json` (regenerated) plus per-exam default instructions in
`app/features/rubrics/profiles/<exam>.json` (field-id → instructions). These are shown by "Generate
draft instructions" in the builder, the same pattern as station `generation_profiles/_generated`.

### 5.2 Exact-match contract test (`tests/contract/test_rubric_matches_legacy_model.py`)

- For each exam, parse the seeded rubric, derive the display schema and compare it with the b2c legacy schema.
- It reuses `marking_content`, `reachable_defs`, `leaf_differences` and `METADATA_FIELDS` from
  `test_feedback_model_parity.py`.
- Normalise only titles, `$ref` inlining and strict-mode wrapping.
- **Zero leaf differences allowed**, covering every field, type, bound, enum, required flag and nullable,
  with **one named exception**: SCA's rating `score` carries the R/A/G enum where legacy had a bare
  string. The test lists that exact path as allowed; any other difference fails. (Decided 2026-09-30: an
  unconstrained rating would let the marker return "Green" or "B" and leave `validate_scores` nothing to check.)
- A second assertion checks that the marker schema equals the display schema minus the `system`
  fields. A third checks that the descriptions contain the legacy description text.

### 5.3 Defaults for rubrics with no exam model (institutions)

- `app/features/rubrics/profiles/_generic.json` holds default instructions per **role**. For example,
  `improvement`: "List what the candidate missed or did poorly, each as one short point tied to the
  transcript."
- The inspector falls back to it when a field has no exam-model default.

---

## 6. Marking and scoring (backend)

- **Engine (`assessment-platform`), small because `Rating` already exists:**
  - `contracts/framework.py`:
    - add an optional `field_roles: Mapping[str, str]` (field id → role, for competency and domain
      fields) and `nullable` on `CompetencyDomain`, if they are not there yet;
    - keep `extra="forbid"`;
    - add tests in `tests/test_framework_contract.py` for each rating kind and for a nullable domain.
  - `prompts/debrief_feedback.py` and `prompts/_tutor_brief.py`:
    - replace the per-exam key reads (SCA `supporting_phrase`, PLAB `critical_flags`, Ortho
      `score_justification`, /10, /50) with a walk by role through the framework;
    - rating wording comes from `rating` (e.g. "7/10", "competent", "Amber").
  - The engine stays platform-agnostic (memory `livekit-layer-platform-agnostic`).
- **platform-api `tutor_memory/domain.py`:** read by role as well.
- **One scoring helper**, `rubrics/scoring.py` (new; it absorbs `reviews/scoring.py`'s arithmetic):
  - `rating_fraction(structure, value) -> float | None` returns 0..1 of the rating's max: R/A/G by scale
    position (G=1, A=⅔, R=⅓, which preserves today's 100/66/33 ratio for SCA), a range as value/max, a
    boolean as 1 or 0.
  - `domain_value`, `total_value` and `passed` implement §4. `passed` includes `requireEveryDomain`.
  - `critical_count` is the number of non-empty `flag`-role fields plus the ratings in the `poor` tone.
  - `combine_reviewers(values)` merges several reviewers' marks: rag/scale takes the majority with today's
    tie-break toward the worse rating, range takes the mean, and boolean takes the majority with a tie
    resolving to false.
- **Callers migrated in the same stage, with the old code deleted:**
  - `reviews/scoring.py`: `RAG_SCORES`, `majority_rag` and `score_for` are removed. `SCORE_SUFFIX` becomes
    `rating.field`. `domain_scores`, `station_score` and `apply_review_overrides` delegate to the new helper.
  - `reviews/domain.py`: `RAG_VALUES` is removed.
  - `dashboard/performance.py` and `service_performance.py`: native per-domain values, the total trend,
    `critical_count`, and the resolved display in the payload.
  - `dashboard/service_cohort.py`, `service_report.py`, `service_report_csv.py` and `service_readout.py`:
    rank and report using `total_value` as a fraction of max and `passed`. The readout's "how scores are
    calculated" text is generated from the display.
  - `results/service_candidate.py`: the station score is `total_value`.
- **Frozen display.** `attempts/domain_definition.py` also freezes the resolved display, so an attempt is
  always shown with its own rules.
- **Changing a rubric mid-cohort:**
  - Every attempt is scored with its own frozen version.
  - Trends and cohort ranks compare the fraction of max.
  - Pass lines drawn on the dashboard are the current version's.
  - The payload carries `mixed_versions: true` and the UI shows "Scored under N rubric versions".
- **Legacy-b2c attempts** (rows tagged `legacy-b2c`, no frozen rubric) are read with the exam's first v2
  platform rubric version. The §5.2 test proves their shape matches.

---

## 7. Candidate feedback and dashboards (platform-web)

- **One renderer, `src/capabilities/feedback/RubricFeedback.tsx`.** Its inputs are the attempt's result, the
  frozen rubric and the resolved display, all served by the attempt read (memory
  `candidate-reads-a-station-through-its-attempt`). Add them to the attempt feedback response if they are
  missing, then regenerate the types.
  - **Header:** station total (`total`, `max`), pass pill (`passed`), band label.
  - **Per domain section:** the title, then the domain aggregate (G/A/R counts, x/4, x% achieved or mean /10)
    with a pass line. Then each competency:
    - its rating, by kind: `GradeCircle` for rag/scale, a tone-coloured "x / max" chip for range, and a
      tick or cross for boolean;
    - its other fields, by role: `evidence` as a quote, `explanation` as a paragraph, `strength` /
      `improvement` / `action` as lists under icons, and `flag` in critical style;
    - the descriptors as a "what good looks like" hint (this replaces `CascCompetencyTable`'s
      hard-coded copy).
  - **Domain `fields`** (CASC generic domains) render under the domain.
  - **`section` fields:** `group` becomes a titled card, `records` becomes a card list (SCA priority
    actions), and `singleSelect` becomes a tag.
  - **Nullable domains** that are null are hidden.
  - **Layout order** follows the rubric's section order. Visual style follows `docs/DESIGN.md`.
- **Candidate dashboard.** `ExamDashboard` and `CompetencyHero` draw only from the served performance
  payload and display:
  - the domain bars use `domain.aggregate` and its pass line;
  - the trend chart uses `total` with `passAtLeast`;
  - the strong and growth cards use `passed`;
  - the donut appears for `ragShare`;
  - all copy comes from `labels`.
  - `examConfig.ts` keeps only non-scoring navigation; its scoring block is deleted.
- **Examiner and GP-lead forms.** `domains/assess/SlotReview.tsx`, `results/GpLeadReview.tsx` and
  `results/SlotReviewers.tsx` generate their inputs from the rubric: a rating control by kind, plus the
  review-editable fields. These are the `reviewable_domains` paths, now keyed on `rating.field`.
- **Inspection screens** (`domains/platform/AttemptInspector.tsx`, `assess/trainee/StationRecord.tsx`,
  `results/CandidateCard.tsx`) reuse `RubricFeedback`.
- **Deleted:** `capabilities/feedback/exams/` (all 16 files), `model.ts` and `model.test.ts`, plus
  `FeedbackDomains`/`FeedbackCategories`/`FeedbackClinicalAnalysis`/`FeedbackPriorityAreas` once
  `RubricFeedback` covers them. `ExamFeedback`'s dispatch goes with them.
- **Tests:** component tests render each of the 4 seeded rubrics with a fixture result (taken from a real
  legacy row) and assert the literal text: "3.2/4", "Passed", "75% competencies", "38/50 · band".

---

## 8. Authoring: the institution can do it all alone

- **Rubric builder.** `RubricDetail.tsx` swaps its `JsonField`s for `StructureBuilder kind="rubric"`.
  - It reuses `SectionFilmstrip`, `SectionStage`, `CanvasBlock` and `AddFieldMenu` (offering only the
    §3.2 types).
  - `BlockInspector` handles label, answer format, role, required, nullable and draft instructions. Its
    "Generate draft instructions" button uses the exam profile, else `_generic.json` by role.
  - **A domain section's stage has two panes:** a Competencies list (id, label, instructions,
    descriptors per rating value) and "Every competency answers" (the `competencyFields`), plus
    domain-level fields.
  - **A Rating panel**, at the rubric level, sets kind, bounds, step or scale, and the rating field.
  - **A Results & dashboard panel** edits `display` as forms, not JSON: pickers for aggregates,
    number inputs for pass marks, a "must pass every domain" checkbox, a tones editor, a bands table,
    and labels. Each input shows its default (§4.2) as a placeholder.
  - `structureBuilderOps.ts` and `blockTypeLabels.ts` gain `rating`/`group`/`records`. Nested fields are
    edited in the inspector.
  - `system_prompt` and `pacing` get plain form fields instead of JSON.
- **Validation in the editor.** Publishing calls the §3.3 validator. Errors show on the field they point at
  (`path`), in plain words. Draft saves are allowed while invalid.
- **Live preview**, a side pane with feedback and dashboard tabs:
  - A pure function, `sampleResult(rubric)` in `capabilities/authoring`, makes plausible marks per field
    type (a spread of ratings, 2-item lists).
  - It renders the real `RubricFeedback` and dashboard components against the resolved display. The
    display resolution is served by `POST /rubrics/{id}/versions/{v}/preview`, so defaults are never
    duplicated in the frontend.
- **Trial mark.** `POST .../versions/{v}/trial` takes a pasted transcript, or picks a past attempt of
  the org's own, and runs the same evaluator on the draft.
  - Progress and the result stream over SSE. The result renders in the preview pane.
  - Nothing is stored against a candidate.
  - Rate-limited per org, because it costs model tokens.
  - Owner: marking-owner.
- **Start from a platform rubric.** `POST /orgs/{org}/rubrics/copy` with `{source_rubric_id}` copies a
  published platform rubric into a new org draft, with a new id and owner, preserving display and
  instructions.
  - This is surfaced as a "Start from SCA / PLAB 2 / CASC / Ortho / blank" chooser on "New rubric".
  - The same "start from" already exists for station templates; confirm that in Stage 4 and add it if not.
- **Permissions stay unchanged.** Org admins author and publish via `router_org`; platform admins via
  `router`. Both hit the same service functions, so parity holds by construction.

---

## 9. Proof that a new exam needs no code ("fifth exam")

`tests/integration/test_new_exam_is_data_only.py` in platform-api:

1. **Create an org-owned rubric** with:
   - an integer 1..5 rating;
   - one domain with 3 competencies, each answering `score` + `evidence` + `missed`;
   - one domain-level `strength` list;
   - one narrative `summary` section;
   - `requireEveryDomain`.

   Then publish it.
2. **Derive the schema.** Assert its literal shape.
3. **Build the engine framework** from `framework_payload`, then `validate_scores` a mark and reject an
   out-of-range 6.
4. **Store a marked attempt.** Assert the literal values of `total_value`, `passed` and `critical_count`,
   and that the rubric shows in the performance payload and the sitting report CSV row.

platform-web adds a matching component test: `RubricFeedback` and the dashboard render that rubric's
fixture with literal text. Neither test touches exam-specific code.

The test fails if anyone reintroduces an exam-code branch that this path needs.

---

## 10. Delivery: four stages, each shippable

**Stage 1: Model, generator, exact match** (platform-api; owner: marking-owner) **[x] Done 2026-09-30** (uncommitted)
- Tasks:
  - `structure.py`, `domain.py` (`parse_structure`, `upgrade_structure`), `validation.py`,
    `schema_builder.py`;
  - the generic converter plus `seeds/rubric_hints/*.json`;
  - profiles, and the regenerated `platform-starter.json`;
  - the §5.2 contract test, written red first;
  - a v1→v2 upgrade test on today's stored rubric JSON.
- Confirm from b2c source: the §4.3 values and Ortho band labels; whether `live_coverage` is
  system-written; any `result_schema_override` users.
- Fold in the uncommitted `guidance`/`--fill` work (`guidance` becomes `instructions`).
- Exit: `make ci` is green, the contract test shows zero differences for all 4 exams, and every existing
  rubric parses via upgrade.
- **Stage 1 outcome.** Exit met: `make ci` green (7776 passed); the contract test is clean for all 4
  exams with only the approved SCA `score` enum exception (29 competencies, not 23); all 8 stored
  rubric versions parse; `seed_platform.py --republish` (renamed from `--fill`) bound v2 versions to
  sca/plab/casc/ortho locally, and a second run is a no-op. Confirmed from b2c: SCA `live_coverage` is
  system-written (`feedback_generation_service.py:324`) but has no integer field type, so it stays a
  legacy metadata field and SCA declares no `system` fields; PLAB `requireEveryDomain` is true
  (`PlabFeedbackModel.py:285`). `result_schema_override` had no users outside the rubric routes,
  service, marking snapshot and `app/migration/exams.py`; all removed, the column kept (dropping it
  is a migration, ask first). Deviations:
  - a third section kind, `field`, for a lone top-level field; a nullable domain's outer
    `description` is kept beside its `instructions`;
  - v1 `R,A,G` is upgraded to `G,A,R` (best first); values unchanged;
  - tones are fractions of the rating maximum (Ortho 0.9/0.7/0.4, CASC 0.8/0); nullable domains are
    alternatives, so only the largest counts toward the total max (Ortho 50);
  - `framework_payload` still sends only what engine v0.9.0 accepts; competency ids stay local and are
    qualified `domain.competency` only where two domains share a name (Ortho), so live coverage keeps
    its keys;
  - `parse_structure` also refuses a pass line above the *derived* maximum (this is what wires
    `resolved_display` into production; the reachability guard requires a caller);
  - `draft_instructions` was not kept: it has no caller until the Stage 4 builder. The path scheme
    it would read is documented on `generate_platform_seed.profile_of`, and `profiles/` is generated;
  - `--republish` compares the system prompt as well as the structure;
  - the generator orders children by `required` (the fixtures list `properties` alphabetically) and
    omits an empty `required`;
  - out-of-scope touch: `dashboard/performance.py` now reads domains via
    `rubrics.service.domain_titles` (upgrade on read), else a republished v2 rubric empties it.

**Stage 2: Marking and scoring** (engine + platform-api; owners: marking-owner, attempt-engine-owner for
debrief/tutor, institution-owner for the institution dashboards) **[x] Backend done 2026-09-30** (uncommitted)
- Tasks:
  - `framework_payload` sends the rating;
  - the engine `field_roles` and nullable changes;
  - debrief, tutor brief and tutor memory read by role;
  - `rubrics/scoring.py`, with every §6 caller migrated and `RAG_SCORES`/`RAG_VALUES` deleted;
  - display frozen on attempts;
  - the performance payload carries native values and the display;
  - the §9 backend test;
  - validator limits measured on a real mark per exam.
- Exit: `make ci` and `poetry run pytest -q` are green. The platform-api e2e marks one station per exam
  locally (memory `platform-api-e2e-run-notes`, `platform-api-seed-is-required`), and the stored rows
  validate against the display schema and contain every field.
- **Stage 2 outcome.** Exit met: `make ci` green (7811 passed, `tests/migration` 84 alone),
  assessment-platform 827 passed. The e2e marked one fresh station per exam against a local API and
  worker with the real model; every stored row validates against its frozen rubric's derived schema,
  the feedback route's totals equal `totals_read`, and the debrief prompt built from each real result
  reads natively (SCA RAG counts, PLAB `1.2/4`, CASC "Competent in 0 of 6", Ortho `18/50`). The §9
  test is `tests/integration/test_new_exam_is_data_only.py`. Validator limits measured: SCA 100 marked
  leaves took 31 s to mark, PLAB 72 took 20 s, CASC 24 took 14 s, Ortho 101 (one nullable domain answered)
  took 13 s; `MAX_MARKED_LEAVES = 400` (about 2 min extrapolated) stays. Deviations:
  - `rubrics/scoring.py` is `rubrics/service_scoring.py`: the slice guard only lets another slice import
    `service*`; it re-exports `RubricStructure` and `scoring_domain_ids` for its callers;
  - the shared read shapes (`RatingRead`, `ReviewFormRead`, `ResultTotalsRead`, ...) live in
    `app/core/schemas.py`, because a slice's schemas may not import another's;
  - `rating_percent` moved from `reviews/scoring.py` to `rubrics`; `reviews/scoring.py` keeps only
    the cohort arithmetic (`scores_by_domain`, `station_score`, `effective_ratings`), now native;
  - institution station score = mean of domain percents; a domain's reviewer ratings combine by
    `combine_reviewers` (range: mean; boolean: majority, a tie is not met; scale: the old majority rule),
    and a candidate's overall is `worst_rating`. The GP-lead verdict stays G/A/R;
  - the error code `invalid_rag` is renamed `invalid_rating` (platform-web only sees it in generated types);
  - learner performance aggregates by the display: SCA red counts 0 (was 33), and `pass_rate`/`fail_rate`
    are null for a rubric with no pass line (SCA), a platform-web type change;
  - the sitting CSV gains `score` and `stations_passed` after `overall_rag`; the readout's methodology
    text is generated from the rubric instead of a fixed RAG paragraph;
  - the tutor brief reads `attempts.latest_scored` and gives tones (words), never numbers; tutor memory
    reads strengths, improvements and evidence by field role;
  - the frozen display needed no migration (it rides in the frozen marking snapshot); the review form
    rides on the review reads; feedback is a new `GET /attempts/{id}/feedback`;
  - found by the e2e: the scoring job stored `model_used` inside the marks, so no stored row validated
    against its rubric's schema (`additionalProperties: false`). It is now popped into the row's own
    column (`attempts/jobs.py`); rows stored before keep the extra key, which readers ignore;
  - found by the e2e: `tests/conftest.py` blanked `OPENAI_API_KEY` at import, so the e2e always skipped;
    the key is kept aside and restored only by the e2e fixture. The e2e takes `PLATFORM_E2E_EXAM_CODE`.

**Stage 3: Candidate feedback and dashboards** (platform-web; owner: web-foundation-owner)
- Tasks:
  - the attempt read serves rubric + display, then regenerate the types;
  - `RubricFeedback`, the dashboard rewiring and the examiner forms;
  - delete the per-exam readers, `model.ts` and the `examConfig` scoring;
  - the §7 and §9 component tests.
- Then republish the 4 platform rubrics: `seed_platform.py --republish` (renamed from `--fill`). It
  publishes a new version when the seeded tree differs, then repoints the exam; frozen attempts are
  untouched. Run locally, then `--env staging`.
- Exit: `npm run ci` is green. Browser check (platform-web `verify` skill): each exam's feedback page and
  dashboard sit side by side with b2c for the same legacy attempt, and so do an institution sitting
  report and a GP-lead review.
- Then `--env production`.
- **[x] Frontend done 2026-09-30** (uncommitted; web-foundation-owner). Local only: staging and production
  republish are still owed. `npm run ci` is green (394 tests). The local `--republish` was a no-op because
  the four rubrics already matched the seed. The browser run used the `verify` skill against the local
  platform-api, with evidence in `platform-web/.verify/2026-09-30T12-36-52-275Z-rubric-stage3` and
  `...12-40-34-952Z-staff-inspector`.
  - **What each exam showed:**
    - SCA: feedback "10% of ratings at G"; the dashboard titled "Where you stand" / "RAG mix by clinical
      domain"; the review form with G/A/R per competency; the reviewers panel "Agreed: R"; the results page
      "overall R".
    - PLAB: "4.6/12", "Pass at 7/12", and "Pass (7/12)" on the dashboard.
    - CASC: "20%", "Pass at 80%", "Pass (80%)", and a Met / Not met form.
    - Ortho: "18/50", "Fair", "Pass at 35/50", "Good (7/10)", band "0–17", and a form of 10..0 buttons.
    - The staff AttemptInspector shows the same feedback.
  - **What was deleted:**
    - `capabilities/feedback/exams/*` (the per-exam readers);
    - `model.ts`;
    - the Feedback{Domains,Categories,ClinicalAnalysis,PriorityAreas,View} components;
    - `dashboard/examConfig.ts` and `insights.ts`, with their tests;
    - the inline G/A/R lists and label maps in the GP-lead, examiner, reviewers, candidate-card and
      my-review screens.
  - **Deviations:**
    - The §7/§9 tests are view-model tests (`rubricView.test.ts`, `rubric.test.ts`, `dashboardView.test.ts`,
      `reviewForm.test.ts`). The test runner cannot render JSX, so they assert the literal strings the
      components print, including a made-up fifth exam.
    - The dashboard's about copy is generic, and every dashboard opens with a Welcome line.
    - The GP-lead overall verdict stays G/A/R and reads "Green / Amber / Red".
    - Where no display tones are sent (review summaries, the cohort report), a rating is coloured by
      position: the first scale value is success, the last is danger. A range is coloured by thirds.
    - `MySlotReviewRead` had no domain labels, so the trainee's own review humanised domain ids (fixed
      2026-09-30 as R-2: every review summary reads `domain_labels`).
    - Comparing side by side with b2c was done against what b2c's code computes (its pass lines, bands and
      RAG shares), not against a running b2c.

**Stage 4: Authoring** (platform-web + platform-api; owners: content-owner for the builder,
marking-owner for trial and copy)
- Tasks:
  - the builder with the Rating and Results & dashboard panels;
  - validation surfaced on fields;
  - the preview endpoint and pane;
  - trial mark over SSE;
  - copy from a platform rubric, and the "start from" chooser.
- **[x] Backend done 2026-09-30** (uncommitted; marking-owner): validation, preview, trial mark over
  SSE, copy, starting points and `draft_instructions`. The builder UI (content-owner / platform-web) and
  the browser exit below are still owed.
- **Stage 4 backend outcome.** `make ci` green (7889 passed). One real trial mark, local DB, real
  model: the seeded SCA rubric copied into a platform draft and trial-marked against a pasted 12-turn
  transcript streamed `connected`, 8 `marking` snapshots, then `marked` in 39 s (gpt-5-mini, 3 domains
  totalled); attempts and result rows were unchanged. Deviations:
  - validation is not its own route: `POST .../rubrics/preview` answers `valid` + every
    `{path, message}` problem, and every version read carries `problems`. A draft now **saves while
    invalid** (create/edit no longer check the structure; pacing and layout still are); publish refuses
    with the same problem list in `details.errors`;
  - preview, copy, starting points and draft instructions are version-less (they take a structure or a
    source), each with a platform and an org route; blank is `copy` with no `source_rubric_id`;
  - the sample result is generated server-side (`authoring.sample_result`, checked against every
    seeded exam's derived schema), not a platform-web pure function, so the preview has one source;
  - `draft_instructions` reads the wording of the rubric the draft was copied from (`basedOn`, written
    by copy) and falls back to `profiles/_generic.json` by role. `profiles/<exam>.json` stay generated
    but unread at runtime: choosing one would need an exam-code mapping;
  - the trial lives in the attempts slice (`service_trial.py`, `router_trial.py`): marking and the
    evaluator are there. It is a `POST` stream, so a browser reads it with `fetch`, not `EventSource`;
    it is rate-limited (20 an hour per org, or per platform admin) and stores nothing;
  - the evaluator now runs the engine in a thread (`asyncio.to_thread`), so a mark no longer blocks
    the event loop; a disconnected trial cannot stop the engine's thread, whose answer is dropped;
  - no migration, no new dependency.
- **[x] Frontend done 2026-09-30** (uncommitted; content-owner). Screens: `/staff/authoring/rubrics/new` and
  `/app/<org>/authoring/rubrics/new` (start chooser), `…/authoring/rubrics/<id>/versions/<v>` (builder) on both
  surfaces; the list's create dialog and JSON edit dialog are gone. Code: `platform-web/src/capabilities/authoring/rubrics/`.
  The builder has Structure (the three section kinds, competencies, competencyFields, every field type with
  role and source), Rating, Results & dashboard (aggregates, pass lines, max, requireEveryDomain, tones,
  bands, labels) and Marking (prompt, pacing, examiner layout) tabs; each backend `{path, message}` is pinned
  under its input; Publish is disabled with the reason shown; the preview draws `RubricFeedback` and the
  real dashboard cards (injected from `domains/train`); the trial streams over `fetch` SSE into `RubricFeedback`.
- **Stage 4 frontend outcome.** `npm run ci` green. Browser, local API: SCA copied as staff, id cleared →
  pinned error, Publish disabled → fixed → both preview tabs → a 5-turn pasted transcript trial-marked
  (`Marked · 46 s`, gpt-5-mini, one streamed request, no polling) → published; then a blank rubric built
  on the org surface (renamed domain, second competency, single field, range rating) → saved → published.
  Evidence `platform-web/.verify/*-rubric-builder`, `*-rubric-blank-org`. Deviations:
  - a dedicated builder, not the station `StructureBuilder` (that is still used for the examiner layout);
  - a trial marks the saved version, so the builder saves a dirty draft first;
  - switching to R/A/G or a named scale drops tones and off-scale descriptors, which the backend refuses;
  - the staging exit (PLAB edit → run an exam → candidate feedback) is still owed: BACKLOG R-8.
- **[x] R-6 and R-7 closed 2026-09-30** (marking-owner). `PATCH /platform/rubrics/{id}` and
  `PATCH /orgs/{org_slug}/rubrics/{id}` (`{title}`, 422 on blank) let the builder header rename a rubric in
  place; `GET .../rubrics/trial-candidates?search=` (owner-scoped, same attempt visibility a trial itself
  checks) backs a picker in `TrialPanel.tsx`, replacing the typed-in attempt id. The shared row shape
  (`TrialCandidateRead`) lives in `app/core/schemas.py`, not either slice's own `schemas.py`
  (`tests/guards/test_schemas_are_not_rows.py`); the cross-slice list call is made from
  `rubrics/service.py`, not the router (`tests/guards/test_routers_are_thin.py`).
- Exit: in a browser, as a staging institution admin (memory `staging-test-accounts`): start from PLAB 2,
  change the pass mark and add a field, see the preview, trial-mark a transcript, publish, run an exam,
  then see the candidate feedback and dashboard reflect the edits. Then build a blank rubric like the
  §9 one entirely in the UI.

**After every stage:**
- update `rubrics/README.md` and the marking-owner notes in `backend/platform-api/AGENTS.md`;
- update the Field Guide artifact (memory `artifact-is-the-reference-surface`) and the B2B journey
  artifact, in plain language;
- record leftovers in `platform-web/docs/BACKLOG.md`.

**Standing rule recorded to memory after approval:** "An exam is data, not code". Each exam's rubric is
the single source for marking, candidate feedback and dashboards; nothing branches on an exam code; a new
exam, or an institution's own, needs only a rubric.

---

## 11. Risks and how the plan handles them

| Risk | Handling |
|---|---|
| The generic renderer looks blander than b2c's bespoke pages | Side-by-side browser checks per exam in Stage 3. Tones, bands and labels are configurable. |
| Institutions author a rubric that marks badly or costs too much | Size limits at publish, preview, trial mark, and starting from a platform rubric. |
| The display vocabulary turns out to be too small for a future exam | Adding an aggregate or pass option is one enum value plus one function in `rubrics/scoring.py`, never an exam branch. The §9 test guards against branching. |
| Old attempts render wrongly | Each attempt has a frozen rubric and display. Legacy rows use the exam's first v2 version, proven by §5.2. |
| A mid-cohort rubric edit skews the dashboards | Fractions of max, current pass lines, and a `mixed_versions` notice. |
| Big-bang rollout | Four stages, each with its own exit proof. Stage 1 changes no behaviour, because v1 is upgraded on read. |

## 12. Owner approvals (granted 2026-09-30)

- **Approved:** delete `result_schema_override` once Stage 1 has listed its users and v2 covers them
  (delete in Stage 1, callers migrated in the same change).
- **Approved:** new routes `/preview`, `/trial`, `/rubrics/copy` (Stage 4).
- No new dependencies or DB migrations expected. If Stage 2 finds the frozen display needs a column,
  ask the owner first.
