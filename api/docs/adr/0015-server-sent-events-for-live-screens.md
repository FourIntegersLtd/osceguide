# 0015. Live screens are pushed as server-sent events, carrying whole read models

Date: 2026-09-17
Status: accepted

## Context
Three screens in this product are live: the supervisor's console during an examination, the
trainee's portal waiting to be called, and the consumer's practice queue. All three were built
as polls — the console every 8 seconds, the portal every 5 — and each poll fanned out into
several requests, because the screen needed a station title, a candidate's name and a marking
flag that lived in different places.

The four read models fixed the fan-out: one request per screen. They did not fix the interval,
and the interval is what the interval costs — a candidate learns it is their turn up to five
seconds late, and an idle organisation with forty tabs open makes half a million requests a day
to be told nothing changed.

b2c already answers this with SSE, and the six hooks in the frontend are written against it. Its
implementation is a dictionary of `queue.Queue` objects in one Python process, and its own log
line admits the consequence: "this worker will deliver events for this key". With a second
worker, an event is published to a subscriber that is not there.

Three things had to be decided rather than inherited: what a frame carries, how fan-out crosses
replicas, and how a browser authenticates a request it cannot put a header on.

## Decision
**Server-sent events, not WebSockets.** The traffic is one-directional — the server tells the
browser that something changed — and every action stays an ordinary authenticated `POST`. SSE
reconnects by itself, survives proxies as plain HTTP, and needs no new protocol in the client.

**Every frame is a whole read model**, the same one the equivalent `GET` returns, rebuilt from
the database when the event arrives. Not a diff and not the writer's idea of what changed. A
client renders a stream and a poll with the same code; a missed event costs a reconnect rather
than a wrong screen; and no second assembly of the same screen exists to drift from the first.

**Fan-out through Redis pub/sub**, behind `core.ports.EventBus`, with an in-process bus when
Redis is off. Events carry a name and nothing else, so no user data crosses the bus and a
subscriber cannot be handed a shape assembled by a publisher who knew less than it does.

**Published after the commit, never inside the service.** `publish_after_commit` queues the
event on the session and `core.db` sends it once the transaction has committed.

**A stream ticket, not a cookie and not the access token.** `EventSource` cannot set an
`Authorization` header. A ticket is the same claims with `typ: "stream"` and sixty seconds to
live; `get_principal` refuses it, so one leaked from a proxy log opens a stream and nothing
else, and not for long. Callers that can set headers send their ordinary bearer instead.

## Consequences
- The 5- and 8-second polls can be deleted from the frontend. Until they are, both routes exist
  and return the same payload, so the switch is per-screen and reversible.
- Redis moves from useful to load-bearing for liveness, though not for correctness: with Redis
  down, a stream still sends its opening snapshot and its heartbeats, and the client falls back
  to the `GET` it replaced.
- A stream holds a connection for as long as a tab is open, so it must never hold the request
  transaction with it. `core.db.stream_session` opens a short transaction per snapshot;
  `get_session_opener` is a dependency so a test can lend a stream its own.
- Tests of a stream cannot use `ASGITransport`, which runs the app to completion and collects
  the body — for a stream, that is a response designed never to end. The `streaming_client`
  fixture runs uvicorn in-process on an ephemeral port instead.
- A streaming route has no `response_model`, so `tests/guards/test_routes.py` gains an exemption
  for `text/event-stream` and, with it, a new requirement: such a route must name the schema its
  frames carry (`core.openapi.sse_responses`), or the generated client hands the caller a string
  to parse by hand — which is how b2c ended up with six drifting payload interfaces.
- Each new live screen is now a few lines: a topic, an announcement after the commit, and a
  snapshot function. The temptation to add a fourth polling loop should not survive that.
