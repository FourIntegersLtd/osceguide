# catalog

## Purpose
The exams the platform publishes, and which organisations offer them.

Two concepts that both legacy backends called an exam. b2c's `app_type` was a
published framework — one of four, the same for everyone — used to index a 4x20
table of Firestore collection names. b2b's `b2b_exams` was an org-scoped row
meaning "this institution runs PLAB prep". ADR 0011 keeps them apart: merging
them would either make the four frameworks org-scoped or make programmes global.

## Use cases
- As **anyone**, I list the exams the platform offers.
- As an **org admin**, I add an exam to my organisation's programme.
- As an **org admin**, I activate or retire a programme.
- As the **platform**, I resolve an exam's engine framework, marking model and
  default timings when an attempt is created.

## Aggregates & invariants
**Exam** is platform-owned and seeded, never created through the API.
**Programme** is org-owned and references an exam.

- There are exactly four exams: `sca`, `plab`, `casc`, `ortho`. They are seeded
  by the migration that creates the table, so a test database has them before
  anything can reference one.
- The seed and `domain.PUBLISHED_EXAMS` must agree; a unit test asserts it,
  because a disagreement is a foreign key pointing at an exam the code does not
  believe exists.
- An exam code is normalised before lookup and an unknown one is refused, never
  defaulted. b2c defaulted to `sca`, which is how CASC ended up marked with a GP
  rubric.
- `exam_id` is `RESTRICT` on delete: an exam with stations or attempts cannot be
  removed out from under them.
- One programme per `(org, exam)`.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/exams` | bearer | the four published exams |
| GET | `/api/v1/orgs/{org_slug}/programmes` | org member | |
| POST | `/api/v1/orgs/{org_slug}/programmes` | org admin | `programme_exists` (409), `unknown_exam` (404) |
| PATCH | `/api/v1/orgs/{org_slug}/programmes/{id}` | org admin | status |

## Jobs
None.

## Cross-slice dependencies
None. `stations` and `attempts` call this slice's service to resolve an exam.
