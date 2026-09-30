# assistant

## Purpose
Sessions where the assistant helps someone use the product: help, onboarding,
dashboard narration and a demonstration consultation. Owns the routes the
LiveKit assistant worker calls.

Distinct from an attempt: nobody is assessed and nothing is marked. What
becomes of the conversation afterwards differs by kind, and is decided above
this slice — see **Three fates** below.

## Use cases
- As a **consumer**, I ask for help by voice and get answers about this product.
- As a **new user**, I am walked through the app.
- As the **assistant worker**, I fetch a session's rendered instructions and the
  tools it may call, ask for the next scene, call a tool and read back a
  sentence to say, deliver the transcript, and report usage when it ends.

## Aggregates & invariants
**AssistantSession** owns its transcript.

- Instructions are rendered backend-side, as an attempt's are. The worker holds
  no templates and refuses a session with blank instructions, so an empty render
  must not reach it.
- b2c's records call one persona `athena-doctor`; the worker's enum calls it
  `consulting-doctor`. That translation happens once, at this boundary — the
  pattern b2c already gets right.
- **Three fates, not two.** `tutor_memory.domain.transcript_policy` decides:
  a **help** session is *retained* as it was — it is a record of somebody
  reporting a problem; a **dashboard** session is *summarised and then deleted*;
  **onboarding** and **consulting-doctor** are *discarded unread*, because they
  are navigation and storing them would record people's screens for nothing. An
  unknown kind discards, which is the safe side.
- **A dashboard session's turns are stored first and deleted by the job that
  replaces them.** They are the only record until the note exists, so the
  summary is queued in the same transaction that wrote them; the job writes a
  `session_summary` note and then calls `discard_transcript`. Discarding at
  delivery would lose the one thing worth keeping; retaining them would keep a
  recording nobody asked for.
- **The tools on the bootstrap are the ones the session was rendered with.**
  They are stored in `extras` when the session starts, not recomposed at
  bootstrap, so what the worker is offered minutes later is exactly what the
  instructions were written against.
- Transcript messages are idempotent on `(session_id, message_id)`.
- A completed session cannot be rejoined.
- The room is derived from the session id, so a stray room says what it is.
- **Only the session's owner may join it.** The token carries the dispatch, so
  issuing one to anybody else would put a stranger in somebody's room and start
  a worker against their history.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/assistant/sessions` | bearer | |
| POST | `/api/v1/assistant/sessions/{id}/voice-token` | bearer | owner only, dispatches the worker |
| GET | `/api/v1/assistant/onboarding-scenes` | bearer | the caller's exam's demo scenes and the assistant's name, for the browser's walkthrough |
| GET | `/api/worker/assistant-sessions/{id}` | worker secret | |
| POST | `/api/worker/assistant-sessions/{id}/scene` | worker secret | |
| POST | `/api/worker/assistant-sessions/{id}/transcript` | worker secret | retained, summarised or discarded by kind |
| POST | `/api/worker/assistant-sessions/{id}/tools/{name}` | worker secret | served by `tutor_memory`, not this slice |
| POST | `/api/worker/sessions/{id}/complete` | worker secret | GPT-Live usage |

**The worker paths are hardcoded in the worker**
(`livekit_assistant_worker/metadata.py:9-12`), not configured per backend as the
assessment worker's are. They must be mounted at exactly these spellings; moving
them breaks the worker. Worth making configurable there — see
`web/docs/BACKLOG.md` A-1.

## Jobs
None of its own. A dashboard transcript causes `tutor_memory` to defer
`summarise_assistant_session`, which comes back through `discard_transcript`.

## Reads for other slices
`service_reads` — `session_ref`, `transcript_messages`, `discard_transcript` —
is what `tutor_memory` needs to know about a session, as plain data rather than
mapped rows. In the other direction this slice calls `tutor_memory` directly:
`service_session.render_dashboard_session` for a dashboard session's
instructions, `service_tools.tool_hook` for tool calls, and `jobs.on_transcript`
to decide whether a transcript is kept.

## Cross-slice dependencies
- `voice.service.grant_for_agent_room` mints the browser's join token and
  decides which deployment the worker runs on. This slice owns who may ask.

A **dashboard** session is rendered by `tutor_memory` from the learner's own
history and carries four backend-defined tools. Everything else is rendered
here: `help` and `onboarding` from the content pack (below), and
`consulting-doctor` from the station in `extras`.

## Content packs
`content/` is b2c's `assistant_content` ported verbatim — pure data and pure
functions, no I/O. `resolve_client_profile` turns the `client` block the
browser sends (surface, route, navigation) plus the caller's exam and role into
a profile; `resolve_content_pack` layers the base packs, then the exam's, then
the surface's, and `overlay.apply` refuses a duplicate or an unknown entry id
rather than letting one silently win.

That layering is the whole point of the `client` block: an FAQ entry that
`requires_nav` is dropped when the screen has no such link, and `{nav.<key>}`
is replaced with the label *this* client uses, so the same pack says "open
Sittings" on an institution screen and "open Mocks" on a consumer one.

A help session carries the entire FAQ inline, as b2c does deliberately — the
model reads every entry itself and there is no search tool. `_INSTRUCTIONS`
survives as a last resort only because `domain.ensure_dispatchable` refuses a
blank instruction; a pack that fails to resolve must still leave something
sayable.

One adaptation: exam identity is `exam_code` here, where b2c used `app_type`.
The `employer` surface is still refused — the employer arm is B2B exam mode,
so a caller declaring one is a bug, not a customer.

Onboarding scenes are frozen into `extras` when the session starts, for the
same reason the tools are: what the worker is offered minutes later must match
the instructions it was given. `POST .../scene` will only render a scene the
session was actually handed.

## Help browser and knowledge chat

Authenticated `GET /api/v1/help/categories`, `/help/articles` (optional category),
and `/help/articles/{slug}` serve the B2C help catalogue bundled in
`help_content.json`, filtered by `app_type` (sca, plab, casc, ortho). This is a
versioned copy of the legacy seed, with the platform's 10-minute booking join
window. Published Firestore edits must be reconciled into this bundle.

`POST /api/v1/help/knowledge-chat` accepts user/assistant message history and
returns a Markdown reply grounded in published summary material. Retrieval is
limited to the requested exam and the caller's server-side study entitlements,
including the 14-day trial. It needs the existing vector index, indexed summaries,
and OpenAI configuration. Missing references yield an explicit no-results answer;
model failures return `knowledge_unavailable`. No legacy Flask request is made.
