# catalog

## Purpose
The exams the platform publishes, and which organisations offer them.

Two concepts that both legacy backends called an exam. b2c's `app_type` was a
published framework — one of four, the same for everyone — used to index a 4x20
table of Firestore collection names. b2b's `b2b_exams` was an org-scoped row
meaning "this institution runs PLAB prep". ADR 0011 keeps them apart: merging
them would either make the four frameworks org-scoped or make programmes global.

## Use cases
- As a **platform admin**, I write an exam, name the rubric it is marked
  against, publish it, and retire it later without touching past attempts.
- As **anyone**, I list the exams the platform offers.
- As an **org admin**, I add an exam to my organisation's programme.
- As an **org admin**, I activate or retire a programme.
- As the **platform**, I resolve an exam's rubric and
  default timings when an attempt is created.

## Aggregates & invariants
**Exam** is platform-owned and authored through the API by a platform admin.
**Programme** is org-owned and references an exam.

- The table **starts empty**. There were exactly four seeded exams, mirrored by
  a frozen tuple in `domain` and pinned to the seed by a unit test, so a fifth
  meant editing both and shipping (ADR 0016).
- `draft` → `published` → `retired`. Only a **published** exam may be built on:
  programmes, entitlements, stations and plans all go through `resolve_exam`,
  which refuses anything else as firmly as an exam that does not exist.
- An exam may only be published once it names the rubric version it is marked
  against, and that version must be published and platform-owned — an exam
  belongs to everyone, so it cannot bind one institution's rubric. A check
  constraint, not a convention.
- An exam code is normalised before lookup and an unknown one is refused, never
  defaulted. b2c defaulted to `sca`, which is how CASC ended up marked with a GP
  rubric. A code is never renamed: plans and partner ref ids hold it as a
  string, and renaming would strand them silently.
- `exam_id` is `RESTRICT` on delete: an exam with stations or attempts cannot be
  removed out from under them.
- One programme per `(org, exam)`.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/exams` | bearer | the published exams; a platform admin also sees drafts |
| POST | `/api/v1/platform/exams` | platform admin | created as a draft |
| PATCH | `/api/v1/platform/exams/{id}` | platform admin | everything but the code |
| POST | `/api/v1/platform/exams/{id}/publish` | platform admin | `exam_not_publishable` (409) without a rubric |
| POST | `/api/v1/platform/exams/{id}/retire` | platform admin | past attempts keep working |
| GET | `/api/v1/orgs/{org_slug}/programmes` | org member | |
| POST | `/api/v1/orgs/{org_slug}/programmes` | org admin | `programme_exists` (409), `unknown_exam` (404) |
| PATCH | `/api/v1/orgs/{org_slug}/programmes/{id}` | org admin | status |

## Jobs
None.

## Cross-slice dependencies
None. `stations` and `attempts` call this slice's service to resolve an exam.
