# voice

## Purpose
Getting a candidate and the right LiveKit worker into the same room. Owns token
minting, the routing decision between our own workers and LiveKit Cloud, and the
dispatch metadata a worker is given.

Replaces near-identical copies in both backends: `livekit_agent_routing.py` and
`livekit/agent_routing.py`, plus two token modules and two cloud-capacity
modules sharing one Redis key.

## Use cases
- As a **candidate practising alone**, I get a token that joins me to my
  attempt's room with the right worker waiting.
- As a **candidate in an examination**, I get a token for the circuit's room
  with no worker attached: the circuit dispatches the patient, not my token.
- As an **examiner**, I get a token that lets me hear a consultation and not be
  heard in it.
- As a **circuit**, I put a patient into a room that is already up, and take it
  out again when the station ends.
- As the **platform**, I overflow to our own workers when Cloud concurrency is full.

## Aggregates & invariants
Owns no tables. The decisions are pure and live in `domain.py`.

- A session type belongs to exactly one worker family; an unknown one is an
  error, never a default, because defaulting dispatches a patient simulation to
  the help worker.
- Routing mode is per family. An empty setting means self-hosted — our own
  capacity, not metered Cloud — and an unrecognised value is an error.
- Overflow is one-way. Cloud past its cap falls back to self-hosted; self-hosted
  never spills onto Cloud, because doing that unasked is a bill, not a fallback.
- A worker is given three strings: `attempt_id`, `backend`, `candidate_ref`.
  Everything else it fetches from the bootstrap route, so the dispatch payload
  cannot become a second, drifting copy of the attempt.
- A token is issued only for an attempt the caller owns and which has not
  finished.
- **An `exam_slot` token carries no dispatch.** The consumer path attaches one
  to the candidate's own token, because there is nobody else to bring the
  patient; a circuit has an orchestrator that does it. Attaching one here put a
  second patient in the room beside the first, and both answered.
- **`can_publish=False` is a guarantee, not a UI state.** An examiner's token
  cannot publish audio at all, so a candidate cannot be prompted and the
  transcript stays a record of what they said to the patient. It carries
  `can_publish_data=False` with it: that grant defaults to *true*, so an
  observer who could not speak could still type into the room's data channel.
- The SDK is a declared dependency. `adapter.py` still imports it inside each
  call and degrades to `voice_unavailable`, which is right for a machine with
  no voice configured — and was also why its absence from `pyproject.toml`
  went unnoticed for the life of the project. `tests/guards/test_imports_are_declared.py`
  now insists every import in `app/` resolves to something declared.
- The room is derived from the attempt id, so a stray room says which attempt
  it belongs to.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/attempts/{id}/voice-token` | owner | `attempt_not_joinable` (409), `voice_unavailable` (503) |

`grant_for_room` has no route of its own: it is how `sittings` mints the
candidate's and the examiner's tokens for a circuit's room, which are served
from that slice because being on the circuit is what grants them.

## Jobs
None.

## Cross-slice dependencies
Reads attempts through `attempts`. The LiveKit SDK sits behind
`core.ports.VoiceTokens`, so tests assert what a token was asked to grant
without a LiveKit project existing.
