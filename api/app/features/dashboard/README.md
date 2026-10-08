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
- As a **consumer**, I see how I am doing at one exam — per domain, overall and
  over time — so I know what to practise next.
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
- As a **course lead**, I download the read-out of a finished sitting: the
  ranking, what it adds up to, what it recommends and how it was worked out.
- As a **course lead on exam day**, I see every circuit running in my
  organisation at once — whose station is live, how long is left, how many are
  done, and what has gone wrong — without walking between rooms.

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
| GET | `/api/v1/me/performance` | bearer | per-domain scores, pass/fail/critical rates and a trend for one exam; `?exam_code=`, defaulting to the last attempted; `unknown_exam` (404) |
| GET | `/api/v1/me/sittings` | bearer | what a trainee is rostered onto, whether each slot is joinable, its `attempt_id` once dispatched, and the server clock; `?org_slug=` keeps one workspace; only organisations where the person holds a live database membership count (a revoked trainee sees nothing, a stale token does not hide anything) (the stream takes it too) |
| GET | `/api/v1/orgs/{org_slug}/dashboard` | org member | counts, setup state, recent sittings |
| GET | `/api/v1/orgs/{org_slug}/supervisor/circuits` | org member | the circuits assigned to the caller |
| GET | `/api/v1/orgs/{org_slug}/circuits/{circuit_id}/console` | org member | the whole live-examination screen, with each slot's live `attempt_id` and clock |
| GET | `/api/v1/orgs/{org_slug}/sittings/{sitting_id}/report` | org admin | per candidate: stations sat, marking, reviewers' combined RAG, decision state; `sitting_not_found` (404) |
| GET | `/api/v1/orgs/{org_slug}/sittings/{sitting_id}/cohort` | org member | the sitting's candidates ranked on their effective scores, completion before score; `not_an_exam_sitting` (422) for a training sitting |
| GET | `/api/v1/orgs/{org_slug}/sittings/{sitting_id}/readout` | org admin | the downloadable read-out: that same ranking, plus what the cohort adds up to, the recommendation sentences and the stated method. JSON — the screen writes the file; `not_an_exam_sitting` (422), `sitting_not_found` (404) |
| GET | `/api/v1/me/sittings/stream` | bearer or `?ticket=` | the same payload, pushed (SSE) |
| GET | `/api/v1/orgs/{org_slug}/live` | org staff | every circuit running now, with its clock, its progress and its alerts |
| GET | `/api/v1/orgs/{org_slug}/live/stream` | org staff | the same payload, pushed (SSE) |
| GET | `/api/v1/orgs/{org_slug}/circuits/{circuit_id}/console/stream` | org member | the same payload, pushed (SSE) |
| GET | `/api/v1/platform/directory` | platform admin | the account directory: every account with the facts beside it (signed in, paid, last plan, live access, attempts); `?q=` email or name, `?exam_code=` chosen or held live, `?status=`, `?access=paid\|trial\|not_started`, `?plan_code=` |
| GET | `/api/v1/platform/directory/summary` | platform admin | per published exam: accounts, and how many paid, on trial, not started; plus the unassigned |
| GET | `/api/v1/platform/directory/users/{id}` | platform admin | one account's directory row; `user_not_found` (404) |

## Jobs
None. Anything expensive enough to need caching belongs behind Redis here rather
than in the callers.

## Streaming
Three of these read models are also served as server-sent events (ADR 0015). A
frame carries the whole read model, identical to the `GET`, so a client renders
a stream and a poll with the same code and can be switched between them one
screen at a time. Circuit changes are announced after the commit — to the
circuit's topic for the console, and to each rostered trainee's topic for the
portal, since a trainee may not read a circuit directly.

The exam-day board subscribes to the **organisation's** topic rather than to
each circuit: an admin watching twelve candidates would otherwise hold twelve
streams, and would miss a thirteenth circuit starting.

Frames are pushed when something changes, not on a tick. A client counts down
from `phase_ends_at` between them rather than waiting to be told the time — the
elapsed and remaining figures in a frame are computed against the server's clock
so the first render is right, not so the page can be driven by them.

The board is `OrgStaff`, not `OrgReader`: it names every candidate and how each
is doing, which is not a thing a candidate may read about the people sitting
beside them.

A browser authenticates with a stream ticket (`POST /api/v1/auth/stream-ticket`)
because `EventSource` cannot send a header; see `core.streams` for why that is
not a cookie and not the access token.

## Cross-slice dependencies
Reads `entitlements`, `attempts`, `station_sets`, `sittings`, `stations`,
`roster`, `reviews`, `catalog`, `rubrics`, `billing`, `tenancy` and `identity`
through their services. Nothing depends on it.

The account directory (`service_platform_users.py`) is here for the same
reason as the rest: the retiring B2C admin's user list had seven columns and
each is a different slice's fact. No single slice can answer "has this person paid?" for a page of users.
The page comes from `identity`, is enriched with one bulk read per slice, and
the facets another slice owns (paid, on trial, on a plan, entitled to an exam)
are handed to `identity` as sets of ids rather than joined across tables.

The one error it can answer with, `circuit_not_found`, is `sittings`',
re-exported by `errors.py`: asking for the console of a circuit that is not
yours is the same refusal as asking for the circuit, and the frontend should
not have two codes for it.

## Performance
`service_performance.py` scores each of somebody's marked attempts at one exam
by the rubric it was marked with (`rubrics.service_scoring.result_totals` over
the frozen structure and display), then aggregates: a domain's `value` is in
the rubric's own unit (a sum, a mean, a share) and `score` is its 0-100
fraction, averaged across the attempts that scored it. The payload carries the
rubric's `display` and `rating`, so a chart labels values natively, and says
when the attempts span several rubric versions (`mixed_versions`).

Pass comes from each rubric's own pass line. A rubric with none (SCA) has a
null `pass_rate` and `fail_rate` rather than an invented one; only attempts its
rubric could judge count. Critical concerns are reported separately, because a
passing attempt can still hold a competency worth a conversation.

The rubric's domains come from the marking snapshot rather than from a read of
the rubric, so the ids used here are the keys the result document actually
carries. An exam with nothing marked yet is an empty answer, not a 404.
