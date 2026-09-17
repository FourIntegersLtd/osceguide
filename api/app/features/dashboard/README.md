# dashboard

## Purpose
One call per screen. Every read model the frontend needs lives here: the
learner's home screen, an organisation's, the supervisor's console and the
trainee portal. They own nothing and enforce nothing — a projection is not a
thing anybody owns — which is why they share a slice instead of being grafted
onto `attempts` or `sittings`.

The SCA dashboard currently makes seven requests — four RAG endpoints, a weekly
trend and two marketplace lists — and joins them in the browser. The B2B org
dashboard makes five, four of which exist only to produce a count.

## Use cases
- As a **consumer**, I open the app and see my access, my progress and where I
  left off, in one request.
- As an **institution admin**, I see what my organisation has set up and what
  is still missing, without downloading four lists to count them.
- As a **supervisor**, I see the circuits assigned to me.
- As a **supervisor**, I run an examination from one screen that knows every
  candidate's name, every station's title, which slot is live and which have
  been marked.
- As a **course lead**, I read a whole sitting back: who sat what, what was marked,
  what the reviewers agreed, and where each decision stands.
- As a **trainee**, I see which attempt to ask a voice token for once the patient is dispatched.
- As a **trainee**, I see the sittings I am rostered onto and whether it is my
  turn to join.
- As a **GP lead**, I see how an examination's candidates compare, so I know
  who to review first.

## Aggregates & invariants
None, deliberately. This slice owns no tables and has no `domain.py`: a
dashboard is a projection, not a thing anyone owns, and no rule is enforced
about one. It reads through other slices' services rather than their tables, so
it cannot quietly become a second owner of anyone's data.

Screens change often and the domain should not follow them, which is why this
exists as its own slice rather than as fields grafted onto `attempts`.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/me/dashboard` | bearer | entitlements, per-exam progress, recent attempts, sets |
| GET | `/api/v1/me/sittings` | bearer | what a trainee is rostered onto, whether each slot is joinable, its `attempt_id` once dispatched, and the server clock |
| GET | `/api/v1/orgs/{org_slug}/dashboard` | org member | counts, setup state, recent sittings |
| GET | `/api/v1/orgs/{org_slug}/supervisor/circuits` | org member | the circuits assigned to the caller |
| GET | `/api/v1/orgs/{org_slug}/circuits/{circuit_id}/console` | org member | the whole live-examination screen, with each slot's live `attempt_id` and clock |
| GET | `/api/v1/orgs/{org_slug}/sittings/{sitting_id}/report` | org admin | per candidate: stations sat, marking, reviewers' combined RAG, decision state; `sitting_not_found` (404) |
| GET | `/api/v1/orgs/{org_slug}/sittings/{sitting_id}/cohort` | org member | the sitting's candidates ranked on their effective scores, completion before score; `not_an_exam_sitting` (422) for a training sitting |
| GET | `/api/v1/me/sittings/stream` | bearer or `?ticket=` | the same payload, pushed (SSE) |
| GET | `/api/v1/orgs/{org_slug}/circuits/{circuit_id}/console/stream` | org member | the same payload, pushed (SSE) |

## Jobs
None. Anything expensive enough to need caching belongs behind Redis here rather
than in the callers.

## Streaming
Two of these read models are also served as server-sent events (ADR 0015). A
frame carries the whole read model, identical to the `GET`, so a client renders
a stream and a poll with the same code and can be switched between them one
screen at a time. Circuit changes are announced after the commit — to the
circuit's topic for the console, and to each rostered trainee's topic for the
portal, since a trainee may not read a circuit directly.

A browser authenticates with a stream ticket (`POST /api/v1/auth/stream-ticket`)
because `EventSource` cannot send a header; see `core.streams` for why that is
not a cookie and not the access token.

## Cross-slice dependencies
Reads `entitlements`, `attempts`, `station_sets`, `sittings`, `stations`,
`roster`, `reviews`, `tenancy` and `identity` through their services. Sits at
the top of the layer order and nothing depends on it.

The one error it can answer with, `circuit_not_found`, is `sittings`',
re-exported by `errors.py`: asking for the console of a circuit that is not
yours is the same refusal as asking for the circuit, and the frontend should
not have two codes for it.
