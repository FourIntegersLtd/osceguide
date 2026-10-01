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

## AI generation (template-bound)

Station **Generate draft** uses:

- `structure.generation.profileKey` — exam profile (`sca.station`, `plab.station`, …) with system prompt from B2C `shared_prompts` and per-block hints exported from B2C Pydantic `Field(description=…)` (`generation_profiles/_generated/`).
- Optional `structure.generation.systemPromptAppend`, and `systemPromptOverride` (platform or org) when `profileKey` is `custom`; a published version is frozen, so the prompt it generates with cannot change under it. With no `profileKey`, the exam's `settings.generation.station_prompt_text` applies, then the prompt its key names; an exam that names none uses the neutral `generic.*` prompts, never SCA's.
- Per-block `generationHint` (LLM-only) and author `placeholder` (appended to profile hints when `generationHint` is empty).

Catalog: `GET /api/v1/station-generation-profiles`. Detail responses return **effective** `blockHints` (exported profile JSON + `template_block_hint_supplements.py` for template-only field ids + `platform_overrides.py` where stricter). Re-export hints after B2C model changes: `poetry run python scripts/export_station_generation_profiles.py`.

## Use cases
- As a **platform admin**, I author a station template and a library station, and
  publish both.
- As an **org admin**, I draft a station template, publish a version, and archive an old one.
- As an **org admin**, I write a station against a published template — my own or
  the platform's — and publish it.
- As an **org admin or platform admin** with a library written elsewhere, I upload
  a station as a PDF or Word file. The first upload drafts a template for me to
  review and publish; that file, and every later one, is then copied into the
  published template as a draft station. Nothing is invented: a part the file
  has no text for stays empty, and both empty and reworded parts are listed for
  me to check (`router_imports.py`, `service_imports.py`).
- As a **trainee or supervisor**, I browse the stations available to my organisation,
  which includes the platform library.
- As **anyone following a link to one library station**, I am told what it is
  without being shown what it holds.
- As a **station author**, I read a station's revision history — which versions
  were published, which were withdrawn, and what each said.
- As a **reader** sitting any station — the platform's or another organisation's —
  I report that it is wrong, and a **platform admin** works the queue of those
  reports and closes them with a note.
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
- The org station list is **reader-scoped**: a caller whose only relationship
  to the org is trainee receives each `content` projected onto the
  candidate-facing keys (`domain_content.py`) — the briefs, the scenario, the
  doctor's information — and never the patient's persona or the examiner's
  material. An org admin, an assigned supervisor or a platform admin reads the
  whole document.
- **Opening a library station from a link is still browsing.** The per-station
  read answers with the row the browse page gives — a title and the ids needed
  to bind it — and does not project the document at all: what a candidate may
  read of a station is disclosed by their own attempt, and a link is not an
  attempt. Should a screen ever need candidate-facing material before a station
  is sat, `domain_content.candidate_content` is the only shape it may be served
  in. The revision history, which is every version's whole document including
  the withdrawn ones, is staff-only for the same reason seen from the other side.
- `owner_kind='platform'` requires `org_id IS NULL`; `owner_kind='org'` requires it
  set. A check constraint, not a convention.
- Attempts reference a `station_version`, never a station.
- **A report about a station is a row about that station**, deduped per person by
  a unique `(station_id, user_id)`. It used to be served by `identity` with the
  body discarded and a docstring saying persistence was TODO, while the runner's
  button went on confirming reports nobody received; legacy stored the array on
  the *user's* document, so the content team never saw one and a repeat tap read
  back as a failure. Deduped, because a second tap is the same report — and
  counted per person, because three people saying one case is wrong is the
  signal that decides whether it gets re-reviewed.
- Anyone may report any station, whatever its owner: a reader inside nobody's
  institution can still find a case wrong, and refusing them is how a bad case
  survives. Only the reporter reads their own list; only a platform admin reads
  the queue or closes a row.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/stations` | bearer | platform library, cursor-paginated; **no station content** — browsing is not reading the answers. Scoped to the exams the caller may open: `?exam_code=` must be one of them (`not_entitled`, 403), and omitting it gives theirs rather than everybody's. A platform admin browses the whole catalogue. `?search=` is a fragment of a title, matched in SQL |
| GET | `/api/v1/stations/{station_id}` | bearer | one library station, and the same row the browse page gives — `station_not_found` (404) for anything that is not the library's, which answers a draft and another organisation's own case identically, and `not_entitled` (403) when the station's exam is not one the caller may open. Replaces the browser's walk of every page. See the invariant about reading |
| GET | `/api/v1/stations/{station_id}/versions` | platform admin, or an admin of the org that owns the station | every revision, newest first, whole documents: `station_not_found` (404), `forbidden` (403). The lifecycle had writes and no reader |
| GET | `/api/v1/orgs/{org_slug}/stations` | org member | the org's own; a trainee-only reader gets the candidate-facing projection of each `content` (see the invariant above) |
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
| POST | `/api/v1/me/station-flags` | bearer | report one station. **204 and idempotent** — a second tap is the same report, not a duplicate and not a 400. `station_not_found` (404) |
| GET | `/api/v1/me/station-flags` | bearer | what this person reported, newest first, each with the case's title (resolved server-side; the legacy screen printed "Unknown Station" for anything off the page it had fetched) |
| GET | `/api/v1/platform/station-flags` | platform admin | the queue, **oldest first**, cursor-paginated; `?status=open\|resolved`, omitted for both |
| PATCH | `/api/v1/platform/station-flags/{id}` | platform admin | resolve with a note, or reopen — which clears `resolved_at` so an open row never answers twice. `station_flag_not_found` (404) |

A template says what a station of this kind contains and what each block is
**for**: its `role`. That is what the renderer places blocks by, which is why
one formatter now serves every station — the three it replaced were chosen by
a branch on the exam's code and on who owned the station.

A station version may only be built on a **published** template version (T3).

## Jobs
None. Prompt rendering happens when an attempt is created, in `attempts`.

## Cross-slice dependencies
Calls `catalog` to resolve an exam, `tenancy` for org access, and
`entitlements.service_access` for the exams a reader may open the library of.
