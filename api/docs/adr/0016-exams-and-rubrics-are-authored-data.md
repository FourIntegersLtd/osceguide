# 0016 — Exams and rubrics are authored data, not shipped code

## Context

Four exams were pinned in three places that had to agree:

- `catalog.domain.PUBLISHED_EXAMS`, a frozen tuple of four;
- a `SEED_EXAMS` insert in the migration that created the table, pinned to the
  tuple by a unit test that loaded the migration file by literal path;
- the `osce_assessment` package, which shipped the frameworks themselves — a
  Python constant naming the domains and competencies, one hand-written JSON
  Schema per exam whose `description` strings were the only place the marking
  descriptors existed, and one of three `.txt` system prompts chosen by a dict
  keyed on framework id.

`catalog.service.resolve_exam` checked the tuple *before* it read the table, so
a row inserted by any other means was unreachable. Adding an exam meant editing
the tuple, the seed, the test, the engine's catalogue, a new JSON Schema and a
new prompt file — then releasing the engine and the backend together.

Station rendering had the same shape: three formatters chosen by
`exam_code == "ortho"` and by whether an org or the platform owned the station.
An exam with a document shape of its own needed engine code.

And the tables an institution used to author its own content — station
templates, station schemas, feedback templates — were `org_id NOT NULL`, so the
platform could not author its own. The asymmetry meant the product's own
library was maintained by hand or by import, never through the API.

ADR 0011 already separated `exams` from `org_programmes`. This does not
reopen that: it changes where an exam's *content* comes from.

## Decision

**An exam is a row a platform admin writes.** `exams` starts empty. There is no
seed and no tuple. `POST /api/v1/platform/exams` creates one as a draft;
publishing it requires naming the rubric it is marked against, and only a
published exam may be built on by a programme, an entitlement, a station or a
plan.

**A rubric is authored data, in a slice of its own.** `rubrics` holds the
scale, the domains, the competencies, and — the part that was previously
impossible to edit — what earns each point of the scale on each competency,
plus the marking instructions and the consultation clock. The JSON Schema the
model is constrained by is **derived** from that structure, so the descriptors
an author types are the descriptors the model reads. A raw-schema override
remains as an escape hatch.

A rubric has **no `exam_id`**. An exam names the rubric version it is marked
with, never the other way round, which is what lets an institution author a
rubric without first inventing an exam to hang it on.

**The rubric version's id is the framework id.** `exams.framework_id` and
`exams.feedback_model_key` are dropped. What `attempt_results` records is the
version's own id, so a stored result traces back to the exact wording it was
marked against.

**The marking rubric is frozen onto the attempt.** When an attempt is rendered,
the whole rubric — framework, prompt, pacing — is frozen into its definition
under `evaluation_policy`. Marking reads that and no mutable row, so re-marking
next year reproduces the original rather than using whatever the rubric says by
then. An attempt with no frozen rubric is not queued for marking: it cannot be
reconstructed from an id.

**Everything authored is owned by the platform or by one org**, the shape
`stations` already had: `owner_kind` plus a nullable `org_id` and a check
constraint. That now covers rubrics, feedback templates, station templates and
stations. Two sets of routes over one service — `/platform/...` gated on
`PlatformAdmin`, `/orgs/{org_slug}/...` gated on `OrgAdmin` — and because
`OrgAdmin` sets `allow_platform_admin=False`, neither can author the other's
content. An org reads the platform's and may build on it; never the reverse.

**One renderer.** A station template's blocks each carry a `role`, and the
engine's single `StationPromptFormatter` places blocks by role. The exam-code
branch and the two exam-shaped formatters are deleted. Blocks marked `examiner`
reach the marker and never the live persona — which was one exam's private
behaviour and is now available to any template.

**The engine ships no content.** `osce_assessment.catalog`, `compat/`, the four
`schemas/*.json` and the three exam prompts are deleted. A framework arrives
through a `FrameworkProvider`; platform-api supplies a `FrozenFrameworkProvider`
built from the attempt's own snapshot.

## Consequences

- Adding an exam is: write a rubric, publish it, write the exam, publish it. No
  migration, no release, no engine change.
- A fresh database has nothing in it. The first platform admin is made by
  `make bootstrap-admin`, because granting the right needs somebody who has it;
  every admin after that is made through the API. The legacy importer takes an
  `--exams` file and refuses to run if it does not define an exam the export
  references.
- Marking prompts are per rubric, so CASC no longer silently borrows SCA's —
  that reuse was deliberate and documented, but it was also invisible to the
  people who owned the exam.
- A rubric's structure is stored per attempt (~15 KB of JSONB for a
  29-competency rubric). That is the cost of reproducible marking and it is
  worth paying.
- `growth.PILOT_EXAMS` becomes `exams.partner_pilot`, a flag an admin sets.
- Imported legacy results keep a `{code}-legacy` framework id rather than being
  relabelled with a rubric version. They were not produced by that rubric, and
  saying they were would be a lie the dashboard would then chart.
- Supersedes the "four seeded rows" sentence of ADR 0011, not its decision:
  `exams` and `org_programmes` remain two tables.
