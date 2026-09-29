# catalog

## Purpose
The exams that get assessed, and which organisations run them.

Two concepts that both legacy backends called an exam. b2c's `app_type` was a
published framework — one of four, the same for everyone — used to index a 4x20
table of Firestore collection names. b2b's `b2b_exams` was an org-scoped row
meaning "this institution runs PLAB prep". ADR 0011 keeps them apart: merging
them would either make the four frameworks org-scoped or make programmes global.

An exam has an **owner**. A *platform* exam is the consumer catalogue we
publish. An *org* exam is an institution's own, written without asking us. The
B2B arm used to be able to run only exams we had published, which made a
school's programme a label on a row we happened to have written; a medical
school's finals OSCE is not our product and should not wait on our catalogue.

## Use cases
- As a **platform admin**, I write a consumer exam, name the rubric it is
  marked against, publish it, and retire it later without touching past
  attempts.
- As an **org admin**, I write **my institution's own exam**, against my own
  rubric, and publish it on my own schedule.
- As **anyone**, I list the exams the platform offers.
- As an **org member**, I list my institution's exams and the platform's.
- As an **org admin**, I add an exam — my own or a platform one — to my
  organisation's programme, and activate or retire that programme.
- As the **platform**, I resolve an exam's rubric and default timings when an
  attempt is created.

## Aggregates & invariants
**Exam** is owned by the platform or by an org, exactly as a station or a
rubric is. **Programme** is org-owned and references an exam it can see.

- The table **starts empty**. There were exactly four seeded exams, mirrored by
  a frozen tuple in `domain` and pinned to the seed by a unit test, so a fifth
  meant editing both and shipping (ADR 0016).
- `owner_kind='platform'` requires `org_id IS NULL`; `owner_kind='org'` requires
  it set. A check constraint, not a convention.
- A code is unique **within an owner**, not globally. Two schools may both have
  a `finals`, and a school may have its own `plab` beside ours — one namespace
  would let whoever registered a code first reserve it for everybody.
- Reading is wider than writing. An org sees its own exams plus the platform's
  published ones; the platform sees only its own. Drafts are visible to their
  owner alone, from both sides: we cannot see what a school is drafting and it
  cannot see what we are.
- Only an exam's own owner may edit, publish or retire it, and a stranger's
  exam is refused as `unknown_exam` rather than `forbidden` — whether the other
  side is drafting something is not learnable by trying ids.
- `draft` → `published` → `retired`, per owner. Only a **published** exam may
  be built on: programmes, entitlements, stations and plans all go through
  `resolve_exam`, which refuses anything else as firmly as an exam that does
  not exist.
- The two statuses are separate. Retiring our PLAB leaves every institution's
  programmes and past results untouched, and a school retiring its programme
  changes nothing for anybody else.
- An exam may only be published once it names the rubric version it is marked
  against. A platform exam's must be published and platform-owned — it belongs
  to everyone, so it cannot bind one institution's rubric. An org exam's may be
  its own or a platform one it can already read; otherwise authoring an exam
  would still mean waiting for us to write the rubric.
- `partner_pilot` is consumer-side and is never set on an org exam: a partner
  attribution link is a B2C funnel and cannot name a school's private exam.
- `resolve_exam` takes the caller's scope. Consumer surfaces — the peer queue,
  the marketplace, community, media, the station library — resolve with no org,
  so a school's private exam code is unreachable from outside it.
- A code is normalised before lookup and an unknown one is refused, never
  defaulted. b2c defaulted to `sca`, which is how CASC ended up marked with a
  GP rubric. A code is never renamed: plans and partner ref ids hold it as a
  string, and renaming would strand them silently.
- `exam_id` is `RESTRICT` on delete: an exam with stations or attempts cannot be
  removed out from under them.
- One programme per `(org, exam)`.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/exams` | bearer | the published **platform** exams; a platform admin also sees its drafts |
| POST | `/api/v1/platform/exams` | platform admin | created as a draft |
| PATCH | `/api/v1/platform/exams/{id}` | platform admin | everything but the code |
| POST | `/api/v1/platform/exams/{id}/publish` | platform admin | `exam_not_publishable` (409) without a rubric |
| POST | `/api/v1/platform/exams/{id}/retire` | platform admin | past attempts keep working |
| GET | `/api/v1/orgs/{org_slug}/exams` | org member | the org's own plus the platform's; `?drafts=true` narrows to its own |
| POST | `/api/v1/orgs/{org_slug}/exams` | org admin | the org's own, as a draft |
| PATCH | `/api/v1/orgs/{org_slug}/exams/{id}` | org admin | `unknown_exam` (404) for a platform exam |
| POST | `/api/v1/orgs/{org_slug}/exams/{id}/publish` | org admin | the org's own schedule |
| POST | `/api/v1/orgs/{org_slug}/exams/{id}/retire` | org admin | past sittings keep working |
| GET | `/api/v1/orgs/{org_slug}/exams/catalog` | org admin | published platform exams with `station_count` and `already_imported` (any programme for it) |
| POST | `/api/v1/orgs/{org_slug}/exams/import` | org admin | `{platform_exam_id}` → 201 `{exam}`; writes an active programme, source `imported_osce_guide`, nothing copied. `unknown_exam` (404) unless a published platform exam, `exam_already_imported` (409) |
| GET | `/api/v1/orgs/{org_slug}/programmes` | org member | |
| POST | `/api/v1/orgs/{org_slug}/programmes` | org admin | `programme_exists` (409), `unknown_exam` (404) |
| PATCH | `/api/v1/orgs/{org_slug}/programmes/{id}` | org admin | status |

## Jobs
None.

## Cross-slice dependencies
`rubrics`, to check that the version an exam names is one its owner may use.
`stations` and `attempts` call this slice's service to resolve an exam.
