# stations

## Purpose
The scenarios a candidate can be given, and the machinery for producing them:
templates, versions, and who owns each.

Unifies two things that were never the same table. b2c kept station documents in
four Firestore collections keyed by product; b2b kept org-authored instances
bound to versioned templates in Postgres — and then reached across into b2c's
Firestore to read the platform library. Here a station has an `owner_kind` of
`platform` or `org`, so an attempt points at one column rather than a union of
sources, and nothing has to read another product's database.

## Use cases
- As a **platform admin**, I author a station template and a library station, and
  publish both.
- As an **org admin**, I draft a station template, publish a version, and archive an old one.
- As an **org admin**, I write a station against a published template — my own or
  the platform's — and publish it.
- As a **trainee or supervisor**, I browse the stations available to my organisation,
  which includes the platform library.
- As the **platform**, I resolve a station version into a scenario when an attempt starts.

## Aggregates & invariants
**Station** owns its versions; **StationTemplate** owns its own. Both may be
owned by the platform or by an org (feedback templates moved to `rubrics`,
beside the rubric they narrow).

- A draft may be edited in place; anything published is immutable, because it is
  what past attempts were assessed against. Correcting content means a new version.
- Only a draft may be deleted. Only a published version may be archived.
- A reading brief is editable on any non-archived version — the one documented
  exception, because a brief is presentation rather than assessed content.
- A new version is seeded from the latest **published** version, not the latest
  version, so an abandoned draft cannot silently become the basis of the next one.
- A station instance may only bind a **published** template version, re-checked at publish.
- A circuit may only reference a **published** station.
- `owner_kind='platform'` requires `org_id IS NULL`; `owner_kind='org'` requires it
  set. A check constraint, not a convention.
- Attempts reference a `station_version`, never a station.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/stations` | bearer | platform library, cursor-paginated; **no station content** — browsing is not reading the answers. Scoped to the exams the caller may open: `?exam_code=` must be one of them (`not_entitled`, 403), and omitting it gives theirs rather than everybody's. A platform admin browses the whole catalogue |
| GET | `/api/v1/orgs/{org_slug}/stations` | org member | the org's own plus the library |
| POST | `/api/v1/orgs/{org_slug}/stations` | org admin | |
| POST | `/api/v1/orgs/{org_slug}/stations/{id}/versions` | org admin | seeded from the latest published |
| POST | `/api/v1/orgs/{org_slug}/stations/{id}/versions/{n}/publish` | org admin | `already_published` (409) |
| POST | `/api/v1/orgs/{org_slug}/stations/{id}/versions/{n}/archive` | org admin | `not_archivable` (409) |
| DELETE | `/api/v1/orgs/{org_slug}/stations/{id}/versions/{n}` | org admin | drafts only; `not_deletable` (409) |
| PATCH | `/api/v1/orgs/{org_slug}/stations/{id}/versions/{n}/brief` | org admin | T5: the reading brief is correctable on a published version |
| GET/POST | `/api/v1/orgs/{org_slug}/station-templates` | org admin / org member to read | the shape a station takes |
| POST | `/api/v1/orgs/{org_slug}/station-templates/{id}/versions` | org admin | seeded from the latest published |
| PATCH | `/api/v1/orgs/{org_slug}/station-templates/{id}/versions/{n}` | org admin | drafts only |
| POST | `/api/v1/orgs/{org_slug}/station-templates/{id}/publish` | org admin | publishes the newest version |

| GET/POST | `/api/v1/platform/stations` | platform admin | the library, drafts included |
| POST | `/api/v1/platform/stations/{id}/versions[...]` | platform admin | as the org routes, with `org_id=None` |
| GET/POST | `/api/v1/platform/station-templates[...]` | platform admin | |

A template says what a station of this kind contains and what each block is
**for**: its `role`. That is what the renderer places blocks by, which is why
one formatter now serves every station — the three it replaced were chosen by
a branch on the exam's code and on who owned the station.

A station version may only be built on a **published** template version (T3).

## Jobs
None. Prompt rendering happens when an attempt is created, in `attempts`.

## Cross-slice dependencies
Calls `catalog` to resolve an exam and `tenancy` for org access.
