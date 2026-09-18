# tutor_memory

## Purpose
What the tutor knows about one learner, and everything that follows from
knowing it: the brief it is told before a dashboard session, the tools it may
call during one, and the summaries written when a conversation ends.

The dashboard assistant used to narrate a canned three-area script. This is the
slice that makes it a tutor who remembers — which consultations this doctor
ran and how each went, what a debrief agreed, what they said last time, what
they have been reading.

Sits above `assistant` and `attempts` and is reached from neither: both
announce their moments through `bind_*` seams tied in `app/main.py`.

## Use cases
- As a **doctor**, I talk to a tutor that remembers my recent consultations,
  what we agreed last time, and what I have been reading.
- As a **doctor**, I read everything the tutor holds about me, and delete any
  of it.
- As the **browser**, I report what somebody read, practised or listened to.
- As the **assistant worker**, I call a tool the backend defined and read back
  a sentence the model can say, plus an optional card for the screen.

## Aggregates & invariants
**LearningEvent**, **TutorNote** and **DebriefSummary**.

- **Two sightings of the same thing inside ten minutes are one visit.** A
  doctor who opens a summary, follows a link and comes back has not read it
  twice, and a memory that says so will be spoken back as a pattern.
- **A dashboard transcript is summarised and then deleted.** What the tutor
  needs next time is what was agreed, not a recording of somebody's screen. The
  note is written first; the turns are the only record until it exists.
- **One debrief summary per attempt**, enforced by a unique constraint rather
  than by the job checking first: the queue may deliver twice, and two
  summaries would have the tutor agreeing two different plans.
- **A refusal never names what was refused.** Suggesting something a doctor
  cannot open turns a locked item into an advertisement, so the tutor is told
  only that it could not be put on screen.
- **A stated fact is clipped to 300 characters.** Longer, and it stops being a
  fact and becomes a paragraph the tutor recites.
- Nothing in the brief is invented: every line comes from this person's own
  records, because the prompt forbids the tutor from saying anything else.
- A tool call is validated against its own advertised schema before it runs; a
  model inventing an argument gets a 422, not an answer about the wrong thing.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/me/activity` | bearer | batch of at most 50, 202 |
| GET | `/api/v1/me/tutor-memory` | bearer | everything on file |
| DELETE | `/api/v1/me/tutor-memory/notes/{id}` | bearer | 204 |
| DELETE | `/api/v1/me/tutor-memory?include_debriefs=` | bearer | says how much went |
| POST | `/api/worker/assistant-sessions/{id}/tools/{tool_name}` | worker secret | one tool call |

**The tool path is hardcoded in the worker**
(`livekit_assistant_worker/metadata.py`), not configured per backend. It must be
mounted at exactly this spelling.

## Jobs
| Task | Queue | When |
|---|---|---|
| `summarise_assistant_session` | `summaries` | a dashboard transcript arrives |
| `summarise_debrief` | `summaries` | a debrief's interaction completes |

Both are deferred inside the transaction that recorded the thing they are
about, so the work and the record of it being owed commit together.

## Cross-slice dependencies
- `attempts.service_reads` — recent attempts, their results and a debrief's
  transcript.
- `stations.service_reads` — station titles, and the library a suggestion must
  be in.
- `entitlements.service` + `catalog.service` — whether a suggestion may be made.
- `assistant.service` / `assistant.service_seams` — whose session a tool call
  is on, this session's turns, and discarding them once summarised.

Seams filled in `app/main.py`: `assistant.service_seams.bind_assistant_hooks`
and `attempts.service_worker.bind_interaction_complete_hook`.

`search_material` answers "not configured": the material index is the next
phase, and until it exists the tutor says plainly that it cannot look something
up rather than answering from nothing.
