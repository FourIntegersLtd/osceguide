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
- As a **supervisor**, I start a circuit, and it then runs itself: the patient
  enters when each consultation begins and leaves when it ends, breaks count
  themselves down, and the last station ends the circuit.
- As a **supervisor**, I take hold of a running circuit when something goes
  wrong — pause and resume the clock, extend or reset it, send the patient in
  again, give a station back, jump to another station, move on early, or hand
  the circuit to a human entirely.
- As a **supervisor**, I add a trainee to a circuit already running.
- As an **examiner**, I step into a candidate's room and listen without being
  heard.
- As a **trainee**, I join the room at the start and stay in it for the whole
  examination, watching the same countdown my supervisor does.

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
- Appending trainees is training-only. Jumping to a station is not: an exam
  candidate whose station fails needs moving as much as a training group does,
  and the old training-only rule left nobody able to do it.
- One slot is active at a time, and a break has none at all.
- Timing is clamped here — reading 1–30 minutes, simulation 1–180 — rather than
  in the browser, which is where b2b clamps it today while the API accepts
  anything at all. A supplied zero clamps to the minimum rather than being read
  as absent.
- Breaks exist only in exam mode and only between stations.
- Slots carry no transcript and no feedback. Those belong to the attempt, which
  is what lets a re-dispatch keep the first recording.
- **The clock is the circuit's, and the server's** (D-6). Not the slot's: a
  break belongs to no slot, and a pause must rewrite one deadline rather than
  two. Every screen reads the same `phase_ends_at`, so a refresh loses nothing.
- **A circuit runs itself.** Starting it is the last manual act. Each phase
  schedules the transition that ends it, in the same transaction that writes
  the phase, so the state and the fact that a move is owed land together.
- **`phase_seq` is how a human beats the clock.** Every scheduled transition
  carries the sequence it was scheduled against and does nothing if that has
  moved; every override bumps it. No lease, no claim table, one integer.
- **Every override is recorded** in `circuit_interventions`, with who and why.
- Slot status is real now: `scheduled` → `reading` → `in_consultation` →
  `completed`, or `skipped` where the circuit moved past it. It was written by
  nothing while four read models displayed it.

## Routes
Scheduling (`router.py`):

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET/POST | `/api/v1/orgs/{org_slug}/sittings` | org admin | |
| GET | `/api/v1/orgs/{org_slug}/sittings/{id}` | org member | includes circuits and slots |
| POST | `/api/v1/orgs/{org_slug}/sittings/{id}/circuits` | org admin | `circuit_locked` (409), `trainee_revoked` (409) |
| PUT | `/api/v1/orgs/{org_slug}/circuits/{id}` | org admin | structural edit (C3); `circuit_locked` (409) once a station has been run |
| POST | `/api/v1/orgs/{org_slug}/circuits/{id}/append-trainees` | org staff | training only |

Running (`router_run.py`), all **org staff** — an admin, or the supervisor
assigned to it. Deliberately not `OrgReader`, which admits the candidate sitting
the circuit: every run route used to take it, so a student could end their own
examination.

| Method | Path | Notes |
|---|---|---|
| POST | `/api/v1/orgs/{org_slug}/circuits/{id}/start` | the last manual act; opens the room and the first reading period |
| POST | `/api/v1/orgs/{org_slug}/circuits/{id}/end` | takes the patient out too, which ending never used to do |
| GET | `/api/v1/orgs/{org_slug}/circuits/{id}/edit-lock` | whether the slots may still be rebuilt |
| GET | `/api/v1/orgs/{org_slug}/circuits/{id}/interventions` | who did what to this examination |
| POST | `/api/v1/orgs/{org_slug}/circuits/{id}/observer-token` | an examiner's subscribe-only way in |
| POST | `/api/v1/me/circuits/{id}/join-token` | bearer; being rostered on is the permission |

Overriding (`router_overrides.py`), org staff:

| Method | Path | Notes |
|---|---|---|
| POST | `…/advance` | "this phase is done"; `circuit_paused` (409) |
| POST | `…/pause` · `…/resume` | `circuit_paused` / `circuit_not_paused` (409) |
| POST | `…/extend-clock` · `…/reset-clock` | more time, or the whole phase back |
| POST | `…/resend-patient` | `no_active_station` (409) during a break |
| POST | `…/redo-station` · `…/jump-to` | `slot_not_found` (404) |
| PATCH | `…/auto-advance` | hand the circuit to a human, or back to the clock |

Removed with this change: `switch-turn`, `dispatch-agent` and
`end-consultation`. The clock does all three, and `jump-to` is the general form
of the first.

`GET /api/v1/me/sittings` and the supervisor's console are read models and live
in `dashboard`; this slice answers what they ask it through `service_reads.py`.

## Jobs
`advance_circuit` is the bell: one job per phase, scheduled for the moment that
phase ends, carrying the `phase_seq` it was scheduled against.

`sweep_circuits` runs every minute and is the safety net, not the mechanism — if
it were, every transition would be up to a minute late. It exists for what the
scheduled job cannot cover: the worker was down when a phase ended, a transition
rolled back, or a deploy landed mid-examination. It also ends circuits left live
for twelve hours, which is the reaper this README promised and b2b already did.

A scheduled transition is found by polling, not by notification, so
`worker_fetch_job_polling_seconds` (default 1.0) matters here in a way it does
not for marking.

Every change to a live circuit is announced after the commit
(`announcements.py`) to the circuit's topic, to the organisation's — which is
what makes the exam-day board live without subscribing per circuit — and to
every rostered trainee's. See ADR 0015 and ADR 0018.

## Cross-slice dependencies
Calls `catalog` for programmes, `stations` to bind station versions, `attempts`
to start a slot's attempt, `voice` to put the patient into the room and to mint
a room token, and `tenancy` for org access.
