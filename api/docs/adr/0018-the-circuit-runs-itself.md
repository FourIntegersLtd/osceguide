# 0018. A circuit runs itself, and every override is recorded

Date: 2026-09-18
Status: accepted

## Context
An OSCE runs on a bell. The station starts, the simulated patient is already in
the room, the bell goes, everyone moves; a break has a countdown; the circuit
ends when the last station has been sat. Nobody stands at the front pressing a
button between every pairing, because on a twelve-station circuit that is more
than twenty deliberate acts, each of them a chance to be late.

What we had was the training-room model applied to an examination. A supervisor
started the circuit, then switched the turn, then dispatched the patient, then
ended the consultation, then switched again. In exam mode there was not even a
first move: `switch-turn` was refused outright, so a candidate's twelve stations
needed twelve manual dispatches and nothing said whose turn it was.

The clock made this worse rather than better. D-6 had already moved it onto the
server, which was right, but only a human ever *wrote* it: switching stamped
`reading`, dispatching stamped `simulation`, and nothing at all read
`phase_ends_at` afterwards. A deadline that expires with nobody watching is a
number on a screen, not a clock. Breaks were stored and counted down by nobody.
`slots.status`, `started_at`, `ended_at` and `exam_completed_at` were written by
nothing while four read models displayed them, which is why a finished station
kept offering a join button.

Three other things were true and worth fixing in the same breath. Every route
that ran an examination took `OrgReader`, and `may_read_org` includes trainees —
so the candidate sitting the circuit could start, move and end it. Ending a
circuit nulled the room name and left the agent sitting in a LiveKit room nobody
was coming back to. And a candidate fetching a voice token for a circuit attempt
got one carrying its own agent dispatch, which would have put a second patient
in beside the supervisor's, both answering.

## Decision
**The clock moves from the slot to the circuit.** A break belongs to no slot, and
a pause must rewrite one deadline rather than two. Screens still show a phase
against the active station; they derive it, and the slot columns are dropped
rather than mirrored, because a mirror is exactly the two clocks D-6 removed.

**Each phase schedules the transition that ends it**, in the same transaction
that writes the phase (ADR 0006), so the state and the fact that a move is owed
land together or not at all. The job carries the `phase_seq` it was scheduled
against.

**`phase_seq` is the whole concurrency design.** Every transition and every
override bumps it; a scheduled job whose sequence no longer matches does
nothing. That is how a human beats the clock — no lease, no claim table, one
integer, and a stale job is a no-op rather than an error.

**A minute-by-minute sweeper is the safety net, not the mechanism.** If it were
the mechanism every transition would be up to a minute late. It covers what the
scheduled job cannot: a worker that was down when a phase ended, a transition
that rolled back, a deploy mid-examination. It also ends circuits left live for
twelve hours, which b2b already did and this slice's README has promised since
it was written.

**One machine serves both modes.** A training circuit's slots are its pairings
and it has no breaks, so "rotate the group" and "walk one candidate through
twelve stations" are the same walk over different slots. Training auto-runs by
default like everything else, and `auto_advance` is the switch that hands it
back to a tutor who wants to talk between stations.

**Overrides are first-class and audited.** Pause, resume, extend, reset, send
the patient again, give a station back, jump to another, move on early. Each
writes a row in `circuit_interventions` naming who did it and why. Automation
without these would be worse than the manual runner it replaces — a circuit
nobody could rescue — and an override nobody recorded is one nobody can answer
for when a candidate appeals.

**`jump-to` replaces `switch-turn`, and is allowed in an examination.** The old
rule refused it because in an exam there is no turn to move. There is still no
turn, but there is very much a need to move a candidate when a station's
equipment fails or they arrive late, and refusing it left nobody able to.

**Running an examination is a staff act.** `may_run_circuit` — an org admin or
the assigned supervisor — gates every run and override route. "Examiner" is a
label for the same `supervisor` role, not a role of its own.

**A candidate joins the room once, at the start.** Being rostered onto the
circuit is the permission, so the route is not under an organisation's path: a
candidate should not have to name their institution to sit its examination.
Their identity is their user id, unchanged, because that is the `candidate_ref`
the worker waits for.

**An examiner's token cannot publish.** Subscribe-only, enforced in the token,
because a muted microphone is a UI state and this has to be a guarantee. Their
identity is prefixed `observer-` and never `agent-`, which is what the stale-
patient sweep matches on.

**Nothing changes in the LiveKit worker.** It has no timer, one job is one
attempt, and removing the agent is how a conversation ends — it posts the full
transcript on its way out. So "the bell goes" and "the recording is delivered"
are already the same act.

## Consequences
- The job worker becomes load-bearing for live examinations, not only for
  marking. A deployment with no worker has circuits that start and never move,
  which the sweeper cannot help with because it is itself a job. This is the
  main operational cost of the decision and is called out in `app/worker/main.py`.
- A scheduled job is found by polling rather than by notification, so the
  worker's fetch interval now matters: `worker_fetch_job_polling_seconds`
  defaults to 1.0 rather than procrastinate's 5.0. Five seconds is fine for
  marking and is five seconds of a candidate sitting in silence here.
- `switch-turn`, `dispatch-agent` and `end-consultation` are removed rather than
  aliased. Nothing in the browser calls platform-api for circuits yet, so three
  spellings of one action in `openapi.json` would be debt taken on for no reader.
- The console and the trainee portal gain circuit-level phase, pause and
  deadline fields; the portal's `can_join` is now about the circuit rather than
  the station, because that is what joining actually is.
- `sittings` grew from eight modules to sixteen under the 250-line cap. The
  splits are along real seams — scheduling against running, the walk against the
  step, the clock against the patient, the clock overrides against the station
  rescues — but it is a large slice and worth watching.
- A circuit mid-examination cannot be downgraded into: the clock it is running
  on would not exist. The migration says so.

## Alternatives considered
**A timer in the worker.** It already holds the room and could end its own
session at a deadline. Rejected: the worker would then need to be told how long
a station is, which is exactly the templates-and-rules boundary
`assessment-platform` is built to keep out of it, and a break or a pause has no
worker to tell at all.

**A lease or claim table per circuit.** The usual answer to "two things might
act on this row". Rejected as more machinery than the problem needs: the row
lock already serialises the writes, and `phase_seq` answers the only remaining
question — whether this job is still the one that should run.

**Polling from the browser, as b2b does.** Rejected for the reason ADR 0015
gives, and because it puts the clock back in a tab: an examination that advances
only while somebody has the page open is not an examination.
