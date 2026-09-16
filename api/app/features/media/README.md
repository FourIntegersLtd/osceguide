# media

## Purpose
Study material that is not a station: slide decks, summaries, blog posts and
podcast episodes, and the search across them.

One table with a `kind` rather than four collections per exam. b2c has sixteen
of those, with the same publish-and-read logic copied into each.

## Use cases
- As a **consumer**, I browse published material and read one by its slug.
- As a **consumer**, I search for something and get the best matches.
- As a **platform admin**, I draft material, edit it, and publish it.

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

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/media` | bearer | filter by `kind`, cursor-paginated |
| GET | `/api/v1/media/{slug}` | bearer | `media_not_found` (404) for a draft |
| GET | `/api/v1/media-search?q=` | bearer | `empty_query` (422) |
| POST | `/api/v1/media` | platform admin | `slug_taken` (409) |
| PATCH | `/api/v1/media/{id}` | platform admin | drafts only |
| POST | `/api/v1/media/{id}/publish` | platform admin | indexes it |

## Jobs
None. Slide and podcast generation are not ported — see `docs/OPEN-QUESTIONS.md` M-2.

## Cross-slice dependencies
Calls `catalog` to tag an item with an exam. Search sits behind
`core.ports.VectorIndex`; the provider is undecided (Pinecone today, pgvector a
candidate), so the default implementation indexes nothing and finds nothing
rather than guessing — M-3.
