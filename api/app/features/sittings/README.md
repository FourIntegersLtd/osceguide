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
- As a **supervisor**, I add a trainee to a circuit already running, and say
  which station they take.
- As an **org admin**, I correct a sitting I scheduled wrong — its name, its
  date, the programme it offers — up until somebody is examined against it.
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
- Appending trainees is training-only, and a latecomer is placed at a station
  this circuit already runs. An exam circuit is one candidate by construction
  (C1), so a second person on it is not a late arrival but a second candidate
  sharing one room, one clock and one recording; the equivalent act is another
  circuit on the same sitting, which `POST /sittings/{id}/circuits` allows while
  it is running. b2b refused the same thing ("use Edit circuit for exam
  sessions"), and naming a station the circuit does not run is the structural
  edit, not this one.
- **A sitting's assessment-bearing fields freeze when it begins.** `mode`,
  `sitting_type` and `programme_id` — the last because the rubric is resolved
  from the programme, so it is how the marking basis is changed — cannot move
  once any circuit on the sitting has started. The name and the date never stop
  moving. `mode` freezes earlier still: while there are circuits at all, because
  it is the rule their slots were composed from and this route composes nothing.
  A field *restated* is not a field *changed*, so PUTting the document back
  untouched is a no-op on a running sitting rather than a refusal.
- Nobody is put on a circuit twice; b2b answered that with 409 and here it
  reached the unique index and came back as a 500.
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
- **A sitting is over when every circuit on it has ended** (D-7), not when the
  last running one does: a day with a morning and an afternoon circuit is not
  over at lunchtime. The check sits in `finish`, so all three ways a circuit can
  end go through it. A circuit that was never started holds its sitting open,
  because nothing can tell "not run yet" from "never will be"; ending that
  circuit outright is what closes the sitting.

## Routes
Scheduling (`router.py`):

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET/POST | `/api/v1/orgs/{org_slug}/sittings` | org admin | |
| GET | `/api/v1/orgs/{org_slug}/sittings/{id}` | org member | includes circuits and slots |
| PUT | `/api/v1/orgs/{org_slug}/sittings/{id}` | org admin | partial: only what was sent is written. `sitting_locked` (409) once a circuit has started and an assessment-bearing field changed, `invalid_circuit` (409) for a mode change over existing circuits |
| POST | `/api/v1/orgs/{org_slug}/sittings/{id}/cancel` | org admin | status `cancelled`, kept not deleted; idempotent. `sitting_locked` (409) once a circuit has started (R-7) |
| POST | `/api/v1/orgs/{org_slug}/sittings/{id}/circuits` | org admin | `circuit_locked` (409), `trainee_revoked` (409); `sitting_locked` (409) on a cancelled sitting or once any decision on it is signed off or released (R-7) |
| DELETE | `/api/v1/orgs/{org_slug}/circuits/{id}` | org admin | a circuit never started; `circuit_locked` (409) once it has been (R-7) |
| PUT | `/api/v1/orgs/{org_slug}/circuits/{id}` | org admin | structural edit (C3); `circuit_locked` (409) once a station has been run |
| POST | `/api/v1/orgs/{org_slug}/circuits/{id}/append-trainees` | org staff | training only; each arrival may name its station. `trainee_already_on_circuit`, `station_not_on_circuit`, `invalid_circuit` (409); `sitting_locked` as for adding a circuit |

Running (`router_run.py`), all **org staff** — an admin, or the supervisor
assigned to it. Deliberately not `OrgReader`, which admits the candidate sitting
the circuit: every run route used to take it, so a student could end their own
examination.

| Method | Path | Notes |
|---|---|---|
| POST | `/api/v1/orgs/{org_slug}/circuits/{id}/start` | the last manual act; opens the room and the first reading period; refused with `lead_cannot_run` if the lead has since lost a staff role that may run circuits (R-41) |
| POST | `/api/v1/orgs/{org_slug}/circuits/{id}/end` | takes the patient out too, which ending never used to do |
| GET | `/api/v1/orgs/{org_slug}/circuits/{id}/edit-lock` | whether the slots may still be rebuilt |
| GET | `/api/v1/orgs/{org_slug}/circuits/{id}/interventions` | who did what to this examination |
| POST | `/api/v1/orgs/{org_slug}/circuits/{id}/observer-token` | an examiner's subscribe-only way in |
| POST | `/api/v1/me/circuits/{id}/join-token` | bearer; being rostered on is the permission |
| GET | `/api/v1/me/slots/{id}/brief` | bearer; the slot is theirs | the candidate's reading brief (sections, or Markdown `text`), keyed on the slot because the attempt only exists after dispatch; one read for org and library stations (B50). `circuit_not_started` (409) until the circuit reaches the slot |

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
rolled back, or a deploy landed mid-examination. It also ends circuits whose clock has
had nothing to count for twelve hours (measured from `phase_ends_at`, so a long
day is not abandoned), never a paused one, and writes an `auto_end`
intervention so the history says the reaper did it (R-15). A consultation whose patient was
dispatched over 60s ago and has no recording gets one `auto_resend_patient` per station (R-17).
Each circuit is its own transaction and its own try/except: one that raises (a
LiveKit dispatch failing) is logged with its id and counted in `failed`, never
allowed to stop the sweep, so the job succeeds and the rest still advance.

Taking the patient out of the room (`clear_patient`) is best-effort: ending or
advancing a circuit records the change even when LiveKit is down or
unconfigured. Ending then owes a `clear_room_agents` job (queue `circuits`,
retried) so the agent is taken out once LiveKit answers (R-13). An interrupted
station (redo, jump) goes back to `scheduled`, not `completed`, and the clock
moves on to the first station not yet sat (R-12). `clock_overdue` is raised only
with auto-advance on (R-14). Starting a consultation still fails when the dispatch does.

A run screen also catches a circuit up (S-7): reading the exam-day board or a circuit's console
(and their streams, which snapshot on every heartbeat) calls `jobs.advance_due`, the same `advance_one` the
worker uses, against the sequence just read and under the row lock, so it is idempotent and safe beside the
scheduled job. The board's `worker_running` is false when `procrastinate_workers` has no heartbeat in 60s.

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

Reads `results` in one place only: `service.ensure_sitting_open` asks whether any
decision on the sitting is signed off or released before a circuit or trainee is added.
The import is function-local because `results` imports `sittings`, and a router may not
import another slice to pass the answer in. Editing and starting a circuit call the sync
`ensure_sitting_not_cancelled`: they only refuse a cancelled sitting.
