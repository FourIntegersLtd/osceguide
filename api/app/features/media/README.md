# media

## Purpose
Study material that is not a station: slide decks, summaries, blog posts and
podcast episodes, and the search across them.

One table with a `kind` rather than four collections per exam. b2c has sixteen
of those, with the same publish-and-read logic copied into each.

## Use cases
- As a **consumer**, I browse published material and read one by its slug.
- As a **consumer**, I search for something and get the best matches.
- As a **platform admin**, I draft material, edit it, and publish it, and I
  read bodies on the public listing (the episode player loads its playlist
  from `GET /media`).

## Aggregates & invariants
**MediaItem** stands alone.

- A slug is derived from the title, unique, and truncated at a **word boundary**
  so a shortened URL still reads as words. A title with nothing usable in it is
  an error rather than a blank URL somebody has to guess.
- Only a draft is editable; published material is replaced, not edited in place.
- A draft is **404 to everyone but an admin** — its existence is not public either.
- Indexing happens on publish, not on write, so a draft nobody can read does not
  surface in search.
- Search returns ids; the rows are then read from the database, so an item
  unpublished since it was indexed cannot leak through a stale entry.
- An empty query is refused rather than matching everything, expensively.
- The catalogue is narrowed **in SQL** — by `kind`, by `exam_code`, and by a `q`
  fragment of a title or summary. A client that filtered in the browser had to
  pull the whole library down to do it, and could only ever match the pages it
  had already fetched, so "no matches" meant "not in the first six hundred".
- Material tagged with **no exam is free material** and appears on every exam's
  list, which is what the consumer screens showed. An `exam_code` that names no
  published exam is refused (`unknown_exam`) rather than quietly answering with
  the free material alone.
- `specialty` and `updated_at` on `MediaRead` are **read out of `content`** by
  the projection (`service_reads.py`), not stored in columns: both are fields
  the authoring payload has always carried and only some kinds use, so a column
  for either would be null for most rows. `specialty` takes the first of
  `content.specialties`, falling back to `content.specialty` — the precedence
  both retiring readers used. `updated_at` takes `content.updated_at` (what a
  migrated b2c blog carries, and the date its card printed) and otherwise the
  row's own `updated_at`, which is `created_at` for an item nobody has edited.
  It is never null.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/media` | none; a token unlocks bodies | filter by `kind`, `status`, `exam_code` and `q`; cursor-paginated. `content` is `null` and `locked` true for material whose exam the reader does not hold |
| GET | `/api/v1/media/{slug}` | none; a token unlocks the body | `media_not_found` (404) for a draft. Same locking as the listing |
| GET | `/api/v1/media-search?q=` | bearer | `empty_query` (422). Filter by `kind`; cursor-paginated. Searches only the material the reader holds |
| POST | `/api/v1/media` | platform admin | `slug_taken` (409) |
| PATCH | `/api/v1/media/{id}` | platform admin | drafts only |
| POST | `/api/v1/media/{id}/publish` | platform admin | indexes it |

## Page shape
Both lists answer with a media-local model — `MediaPage` and `MediaSearchPage` —
rather than `core.pagination.Page`. `Page` is `{items, next_cursor}` and is
shared by every slice, so widening it with a count for one screen's sake would
change the contract of thirty endpoints that do not want it, and `core` is not
this slice's to edit. The two fields `Page` had keep their names and meanings,
so a client reading `items` and `next_cursor` is unaffected; `total_count` sits
beside them.

`total_count` is how many items the filters matched, cursor aside — the number a
screen prints as "N found". Before it existed the library printed
`items.length`, which announced "25 found" for a library of six hundred. It
counts rows the reader cannot open too: a locked item is still an item the
filter matched, and it is listed with `locked: true` rather than dropped.

Search pages keyset on `(score, id)`, ties broken by id so a page boundary
neither repeats nor skips a hit. `VectorIndex.search` takes a limit and no
cursor of its own, so the index is asked for its top hundred and paging runs
within that window; there is no page 101, and inventing an offset to reach one
would put back exactly the instability the rest of the API pages without.

## Jobs
None. LLM draft generation for staff authoring lives under `generation` (`POST /api/v1/platform/generate/*`); TTS and slide video render are not ported — see `docs/OPEN-QUESTIONS.md` M-2.

## Who may read a body
The titles are public — the landing page's article rail and a shared link both
need them without a token — and the bodies are not. `content` is the paid half
of the consumer product (the A to Z, the slide decks), so it comes back to a
**platform admin** (authoring and the consumer player both load bodies from the
listing) or to a reader holding a **live** entitlement for that item's exam;
everybody else gets `locked: true` and a `null` body, which is what the
retiring client's 403 and upgrade prompt were. Material tagged with no exam is
free material and is never locked.

New accounts also unlock their registered exam's study library for fourteen
days from account creation, independently of the AI station quota. After that
window, a live entitlement is required. Other exams remain locked.

`specialty` is derived even for an item whose body is withheld. It is a
catalogue facet in the same family as `kind`, `title` and `exam_code`, all of
which are already public, and a locked deck that reported no specialty would
disappear from the facet list on the very screen that offers to unlock it. The
body itself stays gated.

## Cross-slice dependencies
Calls `catalog` to tag an item with an exam, and `entitlements` to decide whose
body a reader may see. Search sits behind
`core.ports.VectorIndex`; the provider is undecided (Pinecone today, pgvector a
candidate), so the default implementation indexes nothing and finds nothing
rather than guessing — M-3.
