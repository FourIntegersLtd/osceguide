# assistant

## Purpose
Sessions where the assistant helps someone use the product: help, onboarding,
dashboard narration and a demonstration consultation. Owns the routes the
LiveKit assistant worker calls.

Distinct from an attempt: nobody is assessed, nothing is marked, and only one of
the four kinds keeps a transcript.

## Use cases
- As a **consumer**, I ask for help by voice and get answers about this product.
- As a **new user**, I am walked through the app.
- As the **assistant worker**, I fetch a session's rendered instructions, ask for
  the next scene, deliver a help transcript, and report usage when it ends.

## Aggregates & invariants
**AssistantSession** owns its transcript.

- Instructions are rendered backend-side, as an attempt's are. The worker holds
  no templates and refuses a session with blank instructions, so an empty render
  must not reach it.
- b2c's records call one persona `athena-doctor`; the worker's enum calls it
  `consulting-doctor`. That translation happens once, at this boundary — the
  pattern b2c already gets right.
- **Only help sessions keep a transcript.** The other three are navigation, and
  storing them would collect recordings of people's screens for no purpose.
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
| GET | `/api/worker/assistant-sessions/{id}` | worker secret | |
| POST | `/api/worker/assistant-sessions/{id}/scene` | worker secret | |
| POST | `/api/worker/assistant-sessions/{id}/transcript` | worker secret | help only |
| POST | `/api/worker/sessions/{id}/complete` | worker secret | GPT-Live usage |

**The worker paths are hardcoded in the worker**
(`livekit_assistant_worker/metadata.py:9-12`), not configured per backend as the
assessment worker's are. They must be mounted at exactly these spellings; moving
them breaks the worker. Worth making configurable there — see
`docs/OPEN-QUESTIONS.md` A-1.

## Jobs
None.

## Cross-slice dependencies
- `voice.service.grant_for_agent_room` mints the browser's join token and
  decides which deployment the worker runs on. This slice owns who may ask.

Content packs and the FAQ block are not yet ported; instructions are
placeholder text (A-2).
