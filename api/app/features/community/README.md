# community

## Purpose
Questions, replies and station comments.

One `posts` table with a self-referencing parent rather than separate tables per
kind: they are the same shape. b2c has three near-identical collections per
product — twelve in total — and the same handler logic copied across them.

## Use cases
- As a **consumer**, I ask a question and read the answers.
- As a **consumer**, I reply to someone, and like a post.
- As a **consumer**, I comment on a station.
- As an **author**, I delete my own post.
- As a **platform admin**, I remove anything.

## Aggregates & invariants
**Post** is the root; likes and replies hang off it.

- **Removing is authorised.** In b2c, `add_comment`, `delete_comment` and every
  `community/*` route carries no auth decorator at all, so anyone reaching the
  API can delete anyone's post. Here it is your own, anyone's if you moderate
  the platform, or anything addressed inside an institution you administer —
  three permissions rather than one, because conflating them is how the legacy
  routes ended up with none of them.
- **A reply inherits its question's audience** and is never given its own. One
  public answer quoting a private question publishes it.
- **Everything here is addressed to a room** — see `app/core/audience.py`.
  A post, a slot or a queue place is `public`, addressed to one
  `organisation`, or addressed to one `group`. It was addressed to an exam and
  nothing else, so an institution's trainees had no way to talk among
  themselves and a teaching group had no way to practise together. The audience
  is **opaque**: this slice stores a group id and never learns what a group is,
  which is what lets a teaching cohort, a circuit's candidates and a study
  group somebody forms be the same mechanism without reaching up into `roster`
  or `sittings`. A CHECK constraint refuses a row that names a visibility and
  then nobody, because that reads as public to the filter.

- **A like is a row, not a counter.** b2c increments a number, so a double tap
  counts twice and nothing can be undone. Liking is idempotent both ways.
- A question has no parent; a reply must have one. A check constraint, not a
  convention.
- **A question carries tags; a reply never does.** The legacy client let an
  asker tag a question with specialties and the list screen narrow to one.
  Tags describe what a question is about, which is exactly how the feed filter
  uses them, and a reply belongs to its question's thread and topic for the
  same reason it inherits the question's audience — so `CreateReply` has no
  tags field and a reply's `tags` always reads back `[]`.
  - *Storage*: a JSONB array column on `posts`, not a join table. Nothing else
    in the codebase stores a tag-like collection (grep finds no ARRAY columns
    and no shared tag concept in `media` or `catalog` to reuse); the
    established pattern for small document-shaped data on a row is JSONB
    (`media.content`, `sittings.timing`, `rubrics.structure`). A tag is read
    with its post and used to narrow a list, never looked up in its own right
    or shared between rows — the case a join table is for (see `sso`'s
    bindings, which *are* looked up on their own). One containment clause
    (`tags @> '["x"]'`, GIN-indexed) does the filtering.
  - *Validation* (`domain.clean_tags`, beside the content rules): each tag is
    trimmed and lowercased — the legacy client's tags were lowercase specialty
    keys, and a filter matching "Cardiology" but not "cardiology" reads as a
    bug. Blank tags are dropped and duplicates de-duplicated rather than
    refused: the author meant one tag and the list should say so. Over-long
    (> 32 chars, `tag_too_long`) and over-many (> 5 after de-duplication,
    `too_many_tags`) are refusals, because guessing which to drop would post a
    question tagged differently from what its author asked. The legacy route
    stored whatever arrived, unvalidated.
- Removal is soft, so a thread does not lose its shape when one reply goes.
- Content is trimmed at the ends and left alone in the middle — collapsing
  internal whitespace would quietly reformat someone's code block.
- Like and reply counts are fetched for a whole page in two queries, not one
  per post.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET/POST | `/api/v1/community/questions` | bearer | cursor-paginated; `tag` narrows to questions carrying one tag (AND-ed with visibility, so it can only narrow what the caller may see), `tag_too_long`/`too_many_tags` (422) on POST |
| GET/POST | `/api/v1/community/questions/{id}/replies` | bearer | |
| POST/DELETE | `/api/v1/community/posts/{id}/like` | bearer | idempotent both ways |
| DELETE | `/api/v1/community/posts/{id}` | author or platform admin | `post_not_yours` (403) |
| GET/POST | `/api/v1/stations/{id}/comments` | bearer | POST names a station; one that does not exist is `station_not_found` (404), not the foreign key's `internal_error` |

## Jobs
None. b2c moderates comments with an LLM; not ported.

## Cross-slice dependencies
Calls `catalog` to tag a question with an exam, and `stations` to check that a
station a comment names exists.
