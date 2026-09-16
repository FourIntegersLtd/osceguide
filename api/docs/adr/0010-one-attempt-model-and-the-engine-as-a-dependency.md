# 0010. One attempts table, an identity of its own, and the engine as a real dependency

Date: 2026-09-16
Status: accepted

## Context
"A candidate ran a scenario" happens six ways today and is stored six ways. b2c writes a
Firestore voice-session document where `attempt_id == session_id == room_name ==
unified_{uuid}`; b2b writes columns onto `b2b_slots` where `attempt_id == slot_id` and the room
is shared across turns. Both identities are coincidences of implementation that leaked into the
worker contract, and b2b's choice has a consequence: re-dispatching a slot overwrites the single
`transcript` column, so a retried station destroys the first recording.

Both backends already do the important thing correctly. Each freezes a rendered
`AssessmentDefinition` on first bootstrap and replays it verbatim afterwards, so editing a
station tomorrow cannot change what a past attempt was scored against. But each freezes
unconditionally, including when the scenario failed to resolve: a missing station degrades to a
generic patient prompt and an incomplete debrief context degrades to a default prompt carrying
no transcript ids, and that degraded render is then pinned to the attempt permanently.

The engine those definitions come from is vendored into both backends by `git subtree`. The
copies have already drifted — `prompts/debrief_prompt.py` differs between all three while all
three report `__version__ = "0.6.0"` — so the version pin cannot detect it.

## Decision
One `attempts` table for every case, with `id uuid` as its own identity; `room_name` and
`slot_id` become attributes. A `kind` enum with a CHECK that exactly the matching optional
foreign key is set. Re-dispatch creates a new attempt and never overwrites one.

The frozen `AssessmentDefinition` is written **only on a successful render**. A degraded
scenario is served so the session can proceed, and is not persisted, so a later attempt gets a
correct definition instead of inheriting the failure.

`osce_assessment` ships as a versioned dependency from a git tag, not a vendored subtree.

## Consequences
- Transcripts, results and definitions hang off one aggregate, so "show me this candidate's
  attempts" is one query rather than two backends and four collections.
- A retried station keeps both recordings, which the current b2b schema cannot express.
- Drift between engine copies becomes impossible rather than merely detectable.
- The worker contract is unchanged: it still receives an opaque `attempt_id`.
- The migration must mint attempt ids for historical b2c sessions and b2b slots, and keep the
  old identifiers as attributes so existing rooms and slots still resolve.
