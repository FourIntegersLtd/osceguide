# tutor_memory

## Purpose
What the tutor knows about one learner, and everything that follows from
knowing it: the brief it is told before a dashboard session, the tools it may
call during one, and the summaries written when a conversation ends.

The dashboard assistant used to narrate a canned three-area script. This is the
slice that makes it a tutor who remembers — which consultations this doctor
ran and how each went, what a debrief agreed, what they said last time, what
they have been reading.

`assistant` and `attempts` call its services directly when a session renders or an
interaction completes.

## Use cases
- As a **doctor**, I talk to a tutor that remembers my recent consultations,
  what we agreed last time, and what I have been reading.
- As a **doctor**, I tell the tutor I have done something we agreed, and it stops
  asking me about it.
- As a **doctor**, I read everything the tutor holds about me, and delete any
  of it.
- As the **browser**, I report what somebody read, practised or listened to.
- As the **assistant worker**, I call a tool the backend defined and read back
  a sentence the model can say, plus an optional card for the screen.

## Aggregates & invariants
**LearningEvent**, **TutorNote**, **DebriefSummary** and **MaterialChunk**.

- **An agreed step can be ticked off.** `action_plan[].done` was written `false`
  by the summariser and set true by nothing, so `open_action_items` filtered
  nothing and the brief carried every step ever agreed — the tutor kept asking
  about work finished months ago (T-4). The `mark_done` tool closes it, matching
  the doctor's paraphrase against the most recent debrief that still has that
  step open, and matching nothing rather than guessing: ticking off the wrong
  step means never asking about the one they did not do.
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
- **A doctor is only ever read out of material they hold.** The entitled exams
  are worked out from their grants and handed to the index as a filter applied
  *before* the ranking. Today the A to Z and the slides are gated in the
  browser only, so a tutor reading out of them would be a way round that gate.
- **Help is the one corpus anyone reaches.** The app's help articles are indexed
  as corpus `help`: an article for every exam carries no exam and is searched
  for everybody, including someone with no entitlement at all (an institution
  admin asking how to add a trainee); one written for particular exams is
  indexed once per exam as `<slug>@<code>` and reaches only its holders.
- **A conversation can open on a topic.** `extras.topic {title, kind?, slug?}`
  (validated by `assistant.content.parse_topic`) becomes the brief's `topic`
  block: the greeting names it and the prompt starts there instead of from the
  notes. The title is capped and quoted, so it is a subject and never an
  instruction. Whatever is said about it still comes from `search_material`;
  when the material has nothing the tutor says so and does not fill the gap.
- **The brief knows who and where, but neither is memory.** `learner` is the
  name and exam on the account (an email-shaped name is dropped); `screen` is
  the page the browser's validated client context names, matched to its menu.
- **A suggestion is a station, a piece of reading or a help page.** A UUID ref
  is a station version; a help slug the account's exam shows is help; any other
  slug is a published media item of an exam they hold. Every refusal is the
  same sentence.
- **"I could not look that up" is not "the material does not say".** A
  deployment with no embedding key has no index, and the tutor says the first
  rather than the second — a spoken answer delivers both with equal
  confidence, and only one of them would be true.
- **A station offers its management plan and nothing else.** The patient's
  persona, their hidden history and the examiner's expected answers are what
  the station assesses; indexing them would hand a doctor the answers on
  request. A station with no management plan contributes nothing rather than
  contributing its patient brief.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/me/activity` | bearer | batch of at most 50, 202 |
| GET | `/api/v1/me/tutor-memory` | bearer | everything on file |
| GET | `/api/v1/me/debriefs` | bearer | Cursor-paginated, owner-only history beyond the 20-summary tutor-memory window; includes `source_attempt_id` for station filtering |
| DELETE | `/api/v1/me/tutor-memory/notes/{id}` | bearer | 204 |
| DELETE | `/api/v1/me/tutor-memory?include_debriefs=` | bearer | says how much went |
| POST | `/api/v1/admin/tutor-memory/reindex` | platform admin | rebuilds the material index now; synchronous |
| POST | `/api/worker/assistant-sessions/{id}/tools/{tool_name}` | worker secret | one tool call |

**The tool path is hardcoded in the worker**
(`livekit_assistant_worker/metadata.py`), not configured per backend. It must be
mounted at exactly this spelling.

## Jobs
| Task | Queue | When |
|---|---|---|
| `summarise_assistant_session` | `summaries` | a dashboard transcript arrives |
| `summarise_debrief` | `summaries` | a debrief's interaction completes |
| `reindex_material` | `material` | a library station is published or archived, nightly at 03:17, and on the admin route |

The two summary jobs are deferred inside the transaction that recorded the
thing they are about, so the work and the record of it being owed commit
together.

`reindex_material` is idempotent by construction: every source is upserted by
`(corpus, source_id, chunk_index)` and anything indexed that is no longer
published is dropped. A passage whose text and section are unchanged keeps its
vector, so a run embeds only what was edited — the changed passages of about 96
at a time share one embedding request — and a run that failed half way is
repaired by the next one rather than needing to be unwound. It is abandoned
after 15 minutes, because the same worker runs live examinations' transitions.

## Cross-slice dependencies
- `attempts.service_reads` — recent attempts, their results and a debrief's
  transcript.
- `stations.service_reads` — station titles, and the library a suggestion must
  be in.
- `entitlements.service` + `catalog.service` — whether a suggestion may be made.
- `identity.service_platform` — the learner's name and exam for the brief.
- `media.service` — the slug a media citation or suggestion opens by.
- `assistant.service_help` — the help articles the index holds.
- `assistant.service` / `assistant.service_reads` — whose session a tool call
  is on, this session's turns, and discarding them once summarised.

Called by: `assistant` (session render, tool calls, `on_transcript`) and
`attempts.service_worker` (`on_interaction_complete`).

- `media.service` — the published summaries, slides, podcasts and posts the
  index is built from.

## The material index
`search_material` answers clinical questions out of the study material and
cites what it used. The index is pgvector in this same database (ADR 0019),
behind `core.ports.MaterialIndex` with a fake for every test above it.

- `chunking.py` cuts a document into passages. A port of b2c's
  `management_text_utils.py`, pinned by an oracle: where a chunker cuts decides
  which passage answers a question, so moving a boundary changes a clinical
  answer with no diff anywhere near it. One deliberate difference (T-1): a
  section between two headings longer than `MAX_CHUNK_CHARS` is cut by size too,
  keeping its heading, where b2c emitted it whole past the embedding limit. The
  nightly `reindex_material` job re-cuts existing material on its next run.
- `service_material.py` builds the index: which sources go in, and which are
  retired when they stop being published. It decides the corpora and the
  titles, so a citation and a suggestion name the same thing in the same
  spelling.
- `service_search.py` answers a question out of it. Separate from the building
  because the two fail differently and are read at different times — one is a
  nightly walk of the whole catalogue, the other sits in a voice loop with a
  budget of about 350ms.
- `index.py` is the adapter; `repository_index.py` holds the one query with the
  distance operator in it. `build_material_index` returns `None` — not an empty
  index — where there is no key to embed with.
- `vector_column.py` is the `vector` type. The `pgvector` Python package is
  deliberately not a dependency: the extension does the work.

The local compose file and the test container are pinned to
`pgvector/pgvector:pg16`. A stock Postgres fails at `alembic upgrade head`.

## Clinical guidelines, the second line

The guideline library is Clinical Buddy's, and so is its search. `guidelines.py`
asks Clinical Buddy's API for passages (`POST /api/retrieve`, with the shared
key in `X-Service-Key`) and knows nothing of the index, the embedding model,
the fusion or the reranker behind it: one source of truth, changed in one
place. The library is asked at the same moment as our own material, and its
passages are always labelled as the second line.

| Caller | Passages | Limit on the wait |
|---|---|---|
| Voice tutor (`service_search.answer_question`) | 3, reranked | 1.5 s, then left out |
| Help chat (`assistant/service_knowledge`) | 12, reranked | 10 s |

A question about how the app works (the `help` corpus) never asks it. Any
failure, or `CLINICAL_BUDDY_SERVICE_KEY` being unset (the address defaults to
Clinical Buddy's production API; `CLINICAL_BUDDY_URL` overrides it), means no guideline passages and never an error.
