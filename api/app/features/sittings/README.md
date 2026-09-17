# sittings

## Purpose
Scheduled examinations and training sessions: a **sitting** contains
**circuits**, and a circuit contains **slots** — one trainee at one station.

Renamed from b2b's "sessions" because that word already means three other
things here: a LiveKit room, an HTTP session, and a database session.

## Use cases
- As an **org admin**, I schedule a sitting against a programme and bind a
  published feedback template to it.
- As an **org admin**, I add a circuit with its trainees, stations and timing.
- As a **supervisor**, I start a circuit, move the turn between trainees,
  dispatch the agent, end a consultation, and end the circuit.
- As a **supervisor**, I add a trainee to a circuit already running.
- As a **trainee**, I see the sittings I am rostered onto and run my own slot.

## Aggregates & invariants
**Sitting** owns its circuits; a **Circuit** owns its slots.

- A sitting cannot exist without a published feedback template version bound —
  a `NOT NULL` foreign key, not a service check.
- An exam circuit is one candidate through every station, capped at twelve. A
  training circuit pairs each trainee with one station positionally, so everyone
  starts somewhere and they rotate.
- Structural edits and deletion are refused while a slot is live or any feedback
  exists, because rebuilding the slots would delete the one somebody is sitting.
  `force` overrides it, as in b2b, for when a session has gone wrong mid-circuit.
- Switching the turn and appending trainees are training-only: in an exam each
  candidate runs their own circuit, so there is no turn to move.
- One slot is active at a time.
- Timing is clamped here — reading 1–30 minutes, simulation 1–180 — rather than
  in the browser, which is where b2b clamps it today while the API accepts
  anything at all. A supplied zero clamps to the minimum rather than being read
  as absent.
- Breaks exist only in exam mode and only between stations.
- Slots carry no transcript and no feedback. Those belong to the attempt, which
  is what lets a re-dispatch keep the first recording.
- **The exam clock is the server's** (D-6). Switching the turn stamps the new
  slot `reading` with an end time from the circuit's reading minutes;
  dispatching the agent stamps it `simulation` from the simulation minutes;
  ending the consultation or the circuit clears it. The console and the
  trainee portal read the same `phase_ends_at`, so a refresh loses nothing.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET/POST | `/api/v1/orgs/{org_slug}/sittings` | org admin | |
| GET | `/api/v1/orgs/{org_slug}/sittings/{id}` | org member | includes circuits and slots |
| POST | `/api/v1/orgs/{org_slug}/sittings/{id}/circuits` | org admin | `circuit_locked` (409), `trainee_revoked` (409) |
| PUT | `/api/v1/orgs/{org_slug}/circuits/{id}` | org admin | structural edit (C3); `circuit_locked` (409) once a station has been run |
| POST | `/api/v1/circuits/{id}/start` | supervisor or admin | `circuit_already_ended` (409) |
| POST | `/api/v1/circuits/{id}/switch-turn` | supervisor or admin | training only; starts the slot's reading clock |
| POST | `/api/v1/circuits/{id}/end` | supervisor or admin | |

`GET /api/v1/me/sittings` and the supervisor's console are read models and live
in `dashboard`; this slice answers what they ask it through `service_reads.py`.

## Jobs
A stale-circuit reaper is still to come; b2b ends circuits left live for 12 hours.

Every change to a live circuit is announced after the commit (`announcements.py`)
to the circuit's topic and to every rostered trainee's, which is what the console
and trainee-portal streams in `dashboard` react to. See ADR 0015.

## Cross-slice dependencies
Calls `catalog` for programmes, `stations` to bind station versions, `attempts`
to start a slot's attempt, and `tenancy` for org access.
