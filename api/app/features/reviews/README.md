# reviews

## Purpose
Human judgement about a slot, beside the machine's. Three kinds, which b2b keeps
in one wide table discriminated by a `feedback_kind` column and with **no
foreign keys at all**:

- a **slot review** — a rubric filled in by staff, or by a peer observing;
- a **GP-lead review** — a revisioned second opinion;
- a **circuit review** — the aggregate a supervisor finalises.

Three tables, because they have different owners, lifecycles and uniqueness.

## Use cases
- As a **supervisor**, I fill in the rubric for a slot I watched.
- As a **trainee**, I record feedback on a peer I observed.
- As a **GP lead**, I add a second opinion, and I am told if someone edited it
  since I opened it.
- As a **supervisor**, I finalise one set of notes for a whole circuit.

## Aggregates & invariants
Each kind is its own root, keyed to the slot or circuit it concerns.

- One slot review per person per slot; submitting again edits it. `mine` in the
  path rather than an id, so nobody addresses somebody else's by guessing.
- A GP-lead review is one per slot and revisioned. The client must send the
  revision it last read: two reviewers can hold the same screen open, and
  without it the second save silently overwrites the first. A row predating the
  field counts as revision zero, as b2b treats it, so legacy rows stay writable.
- Completing a review requires every reviewable domain scored. A half-marked
  review shown to a candidate is worse than one openly still in progress, so it
  is refused rather than warned about.
- A rating is R, A or G. Combining several takes the **worst**: when two
  reviewers disagree about a candidate, the lower rating is the one that should
  prompt a conversation.
- A conflict is a 409 with `review_conflict`. b2b's client detects this today by
  matching the words "another user" in an error string.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/orgs/{org_slug}/slots/{id}/reviews` | org member | every review of the slot, plus the combined rating per domain (worst wins) |
| PUT | `/api/v1/orgs/{org_slug}/slots/{id}/reviews/mine` | org member | `review_incomplete` (409) |
| GET/PUT | `/api/v1/orgs/{org_slug}/slots/{id}/gp-lead-review` | institution admin | `review_conflict` (409) |
| POST | `/api/v1/orgs/{org_slug}/circuits/{id}/review/finalize` | org member | |

## Jobs
None.

## Scoring
`scoring.py` is the arithmetic a cohort is ranked on, ported from b2b's
`cohort_scoring.py` and pinned by `tests/unit/test_cohort_scoring_oracle.py`:
R/A/G is worth 33/66/100, a domain takes the majority of its skills with ties
resolving downward, a station is the mean of its domains, and a GP lead's
skill-level rating is *overlaid and recomputed* while a domain-level rating
replaces the domain outright. `dashboard` asks for it through this slice's
service; the numbers decide who a reviewer looks at first, so they belong to
the slice that owns what a rating means.

## Cross-slice dependencies
None outward. `sittings` calls `slot_has_review` to decide whether a circuit is
still editable. The set of reviewable domains comes from the sitting's bound
feedback template and is **not yet wired** — see `docs/OPEN-QUESTIONS.md` R-1.
