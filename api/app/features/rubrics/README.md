# rubrics

## Purpose
What a candidate is marked against, and who wrote it.

A rubric is a rating (R/A/G, a scale, a numeric range or yes/no), some
domains, the competencies in each and the fields every competency answers,
written sections, and how feedback and the dashboard read it (`display`) —
plus the marking instructions and the consultation clock. The shape is
`schemaVersion: 2` (plan `docs/plans/rubric-templates.md` §3); a stored
version 1 structure (`scale` + `domains` + `sections`) is upgraded on read by
`domain.upgrade_structure`, so every reader sees version 2 and nothing is
migrated. It used to be three things in the engine package: a Python
constant, a hand-written JSON Schema whose `description` strings were the only
place the descriptors existed, and a `.txt` prompt chosen by a dict keyed on
framework id. Adding an exam was a release. Here it is a row, authored through
the API by the platform or by an institution, and the result schema the model
is constrained by is *derived* from it.

Feedback templates live here too: a feedback template is a narrowing of a
rubric version, so it belongs beside the thing it narrows.

## Use cases
- As a **platform admin**, I write the rubric an exam is marked against, publish
  a version of it, and supersede it later without changing past results.
- As an **org admin**, I write my institution's own rubric, or narrow a platform
  rubric with a feedback template my reviewers work through.
- As the **platform**, I take a marking snapshot when an attempt is rendered, so
  the attempt is marked against the wording it was assessed under.

## Aggregates & invariants
**Rubric** owns its versions. A rubric has an `owner_kind` of `platform` or
`org`, exactly as a station does.

- A draft may be edited in place; anything published is immutable, because it
  is what past attempts were marked against. Correcting it means a new version.
- A new version is seeded from the latest **published** version, so an
  abandoned draft cannot silently become the basis of the next one.
- Publishing validates the structure, the pacing and the prompt. A draft may be
  half-written, and is saved so: every version read carries `problems`
  (`{path, message}`, empty when publishable). Pacing and the marking layout are
  still checked on save. A published version may not be invalid, because
  attempts will be marked against it.
- A copy remembers its source as `structure.basedOn` (`{rubricId, version,
  title}`); validation ignores the key. `draft_instructions` reads it to offer the
  source's own wording, else `profiles/_generic.json` by role.
- A rubric has **no `exam_id`**. An exam names the rubric version it is marked
  with, never the other way round, which is what lets an institution author one
  without inventing an exam to hang it on.
- An exam may only name a **published, platform-owned** version: an exam
  belongs to everyone, so it cannot be bound to one organisation's rubric.
- `owner_kind='platform'` requires `org_id IS NULL`; `owner_kind='org'` requires
  it set. A check constraint, not a convention.
- Competency and domain ids are identifiers, not free text: they become JSON
  property names and are read back by code.
- A descriptor for a value that is not on the rating's scale is refused — it
  would be an instruction the model cannot follow.
- A competency's `descriptors` say what earns each value; its `instructions`
  (and a domain's, and a field's) say what to look for whatever the value. All
  reach the model through the derived schema; instructions never go to the
  engine's `CompetencyFramework`, which forbids unknown fields.
- Every structural rule lives in `validation.py` and reports every problem at
  once as `{path, message}` (`InvalidRubricError.details.errors`), so an editor
  can mark each place. Pass lines are also checked against the *derived*
  maximum (`resolved_display`), not only one the author typed.
- `resolved_display` is the only place display defaults exist (aggregates,
  maxima, tones as fractions of the rating maximum). Ortho's total is 50: a
  nullable domain is one of several alternatives, so only the largest counts.
- Competency ids are unique within a domain, not across the rubric. The
  engine framework keeps each id, qualifying `domain.competency` only where
  two domains share a name (Ortho), because live coverage keys on the id.
- The seed is generated, never hand-edited: `scripts/generate_platform_seed.py`
  reads the legacy models in `tests/fixtures/legacy_schemas` plus the per-exam
  hints in `seeds/rubric_hints/<exam>.json` (the only exam-specific files), and
  writes `seeds/platform-starter.json` and `profiles/`. `seed_platform.py
  --republish` publishes it as a new version and rebinds each exam.
  `result_schema_override` is retired (the column stays until a migration drops it).

## Scoring
`service_scoring.py` is the one place a mark becomes numbers, for every exam:
`result_totals` (per domain and in total, by the display's aggregate, with
pass and critical concerns), `worst_rating`, `combine_reviewers`,
`rating_percent`, `rating_tone`/`tone_for_fraction`, and the by-role readers
the tutor uses (`weakest_domain_tones`, `texts_by_role`). It is named
`service_*` because another slice may only import a slice's services
(`tests/guards/test_slices_call_services_only.py`); it re-exports
`RubricStructure` and `scoring_domain_ids` so callers need nothing else. The
read shapes other slices return (`RatingRead`, `ReviewFormRead`,
`ResultTotalsRead`, ...) live in `app/core/schemas.py`, since a slice's schemas
may not import another's. `service_marking.py` builds them: the engine
framework (`engine_framework`, with the rating, nullable domains and
`field_roles`), the frozen `ScoringRubric` of an attempt
(`frozen_scoring_rubric`), `review_form` and `totals_read`.

A mark is judged by the rubric frozen on the attempt, display included, so a
later republish never re-scores the past. `tests/integration/test_new_exam_is_data_only.py`
proves a rubric nothing in the code has seen marks, totals, reports and
exports end to end.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/platform/rubrics` | platform admin | |
| GET | `/api/v1/platform/rubrics` | platform admin | cursor-paginated |
| GET | `/api/v1/platform/rubrics/{id}` | platform admin | |
| POST | `/api/v1/platform/rubrics/{id}/versions` | platform admin | seeded from the latest published |
| PATCH | `/api/v1/platform/rubrics/{id}/versions/{n}` | platform admin | `not_editable` (409) |
| POST | `/api/v1/platform/rubrics/{id}/versions/{n}/publish` | platform admin | `invalid_rubric` (422) |
| POST | `/api/v1/platform/rubrics/{id}/versions/{n}/archive` | platform admin | `not_archivable` (409) |
| GET | `/api/v1/orgs/{org_slug}/rubrics` | org member | the org's own plus the platform's |
| GET | `/api/v1/platform/rubrics/starting-points?search=` | platform admin | builder's "start from": blank, then published platform rubrics |
| POST | `/api/v1/platform/rubrics/preview` | platform admin | `{structure}` → valid, problems, schemas, display, sample result and totals; never refused |
| POST | `/api/v1/platform/rubrics/copy` | platform admin | `{source_rubric_id?, source_version?, title?}` → a new draft rubric (201); none = blank; `rubric_version_not_published` (409) |
| POST | `/api/v1/platform/rubrics/draft-instructions` | platform admin | `{structure}` → suggested wording per slot; `invalid_rubric` (422) |
| POST | `/api/v1/platform/rubrics/{id}/versions/{n}/trial` | platform admin | SSE, served by `attempts/router_trial.py`; see the attempts README |
| PATCH | `/api/v1/platform/rubrics/{id}` | platform admin | `{title}` (R-7); every version keeps the new title, so no version is touched |
| GET | `/api/v1/platform/rubrics/trial-candidates?search=` | platform admin | cursor-paginated attempts this owner could trial-mark (R-6); row shape is `core.schemas.TrialCandidateRead` |
| GET/POST | `/api/v1/orgs/{org_slug}/rubrics/...` | org admin | the same fourteen, org-owned (starting points add the org's own) |

## Jobs
None. A marking snapshot is taken when an attempt is rendered, in `attempts`.

## Cross-slice dependencies
`catalog`, `stations`, `sittings`, `reviews` and `attempts` call this slice's
service. The other direction: `service.trial_candidates` (R-6) calls
`attempts.service_trial.trial_candidates` to list attempts this owner could
trial-mark against — a thin wrapper, so the router still names only its own
slice's `service`/`schemas` (`tests/guards/test_routers_are_thin.py`).
