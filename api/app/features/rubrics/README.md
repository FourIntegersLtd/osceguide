# rubrics

## Purpose
What a candidate is marked against, and who wrote it.

A rubric is a scale, some domains, the competencies in each, and what earns
each point of the scale on each one — plus the marking instructions and the
consultation clock. It used to be three things in the engine package: a Python
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
  half-written; a published version may not, because attempts will be marked
  against it.
- A rubric has **no `exam_id`**. An exam names the rubric version it is marked
  with, never the other way round, which is what lets an institution author one
  without inventing an exam to hang it on.
- An exam may only name a **published, platform-owned** version: an exam
  belongs to everyone, so it cannot be bound to one organisation's rubric.
- `owner_kind='platform'` requires `org_id IS NULL`; `owner_kind='org'` requires
  it set. A check constraint, not a convention.
- Competency and domain ids are identifiers, not free text: they become JSON
  property names and are read back by code.
- A descriptor for a score that is not on the scale is refused — it would be an
  instruction the model cannot follow.

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
| GET/POST | `/api/v1/orgs/{org_slug}/rubrics/...` | org admin | the same seven, org-owned |

## Jobs
None. A marking snapshot is taken when an attempt is rendered, in `attempts`.

## Cross-slice dependencies
None. `catalog`, `stations`, `sittings`, `reviews` and `attempts` call this
slice's service.
