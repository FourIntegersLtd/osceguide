# voice

## Purpose
Getting a candidate and the right LiveKit worker into the same room. Owns token
minting, the routing decision between our own workers and LiveKit Cloud, and the
dispatch metadata a worker is given.

Replaces near-identical copies in both backends: `livekit_agent_routing.py` and
`livekit/agent_routing.py`, plus two token modules and two cloud-capacity
modules sharing one Redis key.

## Use cases
- As a **candidate**, I get a token that joins me to my attempt's room with the
  right worker waiting.
- As a **supervisor**, I get a room-admin token so I can observe a circuit.
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
- The room is derived from the attempt id, so a stray room says which attempt
  it belongs to.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/attempts/{id}/voice-token` | owner | `attempt_not_joinable` (409), `voice_unavailable` (503) |

## Jobs
None.

## Cross-slice dependencies
Reads attempts through `attempts`. The LiveKit SDK sits behind
`core.ports.VoiceTokens`, so tests assert what a token was asked to grant
without a LiveKit project existing.
