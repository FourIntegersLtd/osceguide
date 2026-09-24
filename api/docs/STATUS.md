# Where the platform-api rewrite stands

Built to the method in `CONTRIBUTING.md`: use cases, then guard and contract
tests, then oracles ported from the legacy suites, then the domain, then
storage, then the service and router.

**Read the generated half below before trusting anything here.** An earlier
version of this document described slices as complete while their rules had no
caller and their routes did not exist, so the numbers and the gap lists are now
derived from the code by `scripts/status_report.py`. `make status-check` fails
if they drift.

## What happened in the audit

On 2026-09-16 this work was stopped and reviewed against the architecture
proposal. The review found that **the core did not work**: `attempts.definition`
was written in exactly one place, and the only caller was a test fixture. Every
real attempt had `definition = NULL`, `bootstrap` refused it, and the LiveKit
worker had never been able to run a single station. `tests/e2e/` contained no
tests at all — only a Phase 0 gate whose docstring promised they would "arrive
with the attempts slice".

One process gap explains most of the rest: **domain rules were written with
unit tests, then services were written, and nothing checked that a service
called the rule.** 20 of 101 rules were green, documented in a slice README,
advertised in the OpenAPI error list, and never executed. Every guard checked
*structure*; none checked wiring.

That is what `tests/guards/test_domain_rules_are_reachable.py` now exists to
stop, and its debt list is reproduced below.

## Fixed since the audit

| | |
|---|---|
| Prompt rendering | The backend renders every prompt; the worker holds no templates. An adapter onto the engine's formatters, with A1/A2 wired — the definition is frozen on the first *successful* render, and a degraded one is served but not persisted |
| Prompt oracle | Renders byte-identical to the engine's own golden files for the library and org station shapes |
| End to end | Creation → bootstrap → chunks → transcript → scored result, over real routes, plus an e2e test against the real worker (**run once, locally, on 2026-09-18** — see below) |
| Reachability guard | Fires on a real planted orphan; ratchets a debt list that may only shrink |
| Tenant scoping guard | Was inspecting **zero** functions — it walked `ast.ClassDef` and matched SQL strings, neither of which exists since ADR 0013. Now inspects 41 |
| Cross-tenant write (P4) | Any org admin could store a review against any slot in the system. Reads filtered by org, so it looked contained |
| Org suspension | Was write-only: suspending an organisation restricted nobody |
| Free trial | Never ran, so no new consumer could start anything |
| S1 | A sitting could bind a draft rubric, or another org's |
| Cloud capacity | Counted for the first time, with b2c's scripts byte-identical; the two `livekit-cloud-slot` worker routes served |
| C4 | Row lock plus `ensure_live`. The race reproduced an ended circuit still showing a candidate consulting |
| C5, C6, C3, C8 | Agent dispatch with stale removal, a new attempt per dispatch, the edit lock, and appending latecomers into the live room. Dispatch is now the circuit's own act rather than a route (ADR 0018) |
| The four read models | `/orgs/{slug}/circuits/{id}/console`, `/orgs/{slug}/dashboard`, `/orgs/{slug}/supervisor/circuits` and `/me/sittings` are served. The console replaces a session read, a station list, a trainee list, a staff list and one feedback probe per slot, every eight seconds |
| The circuit runs itself | ADR 0018. Starting a circuit is the last manual act: the patient enters when each consultation begins and leaves when it ends, breaks count down, and the last station ends the circuit. Each phase schedules the transition that ends it in the same transaction, guarded by `phase_seq`; a minute-by-minute sweeper is the safety net and the twelve-hour reaper. The clock moved from the slot to the circuit, because a break belongs to no slot and a pause must rewrite one deadline rather than two |
| Exam-day overrides | Pause, resume, extend, reset, send the patient again, redo a station, jump to another, move on early, hand the circuit to a human — each recorded in `circuit_interventions` with who and why. `jump-to` replaces `switch-turn` and works in an examination, which switching the turn did not |
| Who may run an examination | Every run route took `may_read_org`, which includes trainees — so the candidate sitting the circuit could start, move and end it. `may_run_circuit` is an org admin or the assigned supervisor |
| The exam-day board | `/orgs/{slug}/live` and its stream: every circuit an organisation has running, with elapsed and remaining computed against the server's clock, stations done, and alerts for a consultation with nothing recording it or a phase the clock has got past |
| Joining a room | A candidate joins the circuit once, at the start, and stays — being rostered on is the permission, so the route names no organisation. An examiner joins subscribe-only, enforced in the token. An `exam_slot` voice token no longer carries its own dispatch, which would have put a second patient in the room |
| Live screens | Server-sent events (ADR 0015): the console and the trainee portal are pushed, each frame the whole read model the `GET` returns. Fan-out is Redis pub/sub behind a port, published after the commit, and a browser authenticates with a sixty-second stream ticket because `EventSource` cannot send a header |
| Station templates | The tables were modelled with no repository, service or routes, so `station_versions.template_version_id` could only ever be null. Authored now, and T3 refuses a station built on a template still in draft |
| RAG aggregation | `combine_rag` had no caller, so the console, a released result and any export each worked a candidate's rating out for themselves. The slot reviews route now carries the combined rating per domain, worst wins |
| Partner references | `GET /growth/partners/{p}/ref-ids`: the other half of `parse_ref_id`. A partner was told the spelling in an email and typed `bmj-sca` by hand, and a typo attributes their traffic to nobody |
| Three more rules wired | R3 (a revoked trainee cannot be scheduled), T5 (the reading brief is correctable on a published version) and T6 (a draft may be deleted, a published version archived). `KNOWN_UNWIRED` is down from ten to six |
| C3 has a route | `PUT /orgs/{slug}/circuits/{id}` rebuilds a circuit, refused once a station has been run, feedback recorded or a consultation started. Correcting a circuit meant abandoning it and building another |
| Cross-slice layering | The "a slice calls another slice's service, never its repository" rule had fourteen violations and no guard. Both are fixed: `catalog`, `identity` and `attempts` now answer through their services, and `tests/guards/test_slices_call_services_only.py` keeps it that way |
| Seams | `tests/guards/test_every_seam_is_bound.py`: every `bind_*` is called by `main.py`, and a built app has each one filled in |
| The platform library | `GET /api/v1/stations` is served, cursor-paginated and filtered by exam. It carries no station content: browsing is not reading the answers. The `owner_kind = 'platform'` half of the table had no reader at all |
| Abandon and acknowledge | `POST /attempts/{id}/abandon` (an abandoned attempt stayed `running` forever, holding the slot's one live attempt) and `POST /me/results/{sitting_id}/acknowledge` (one append-only event per revision, idempotent) |
| `trainees.user_id` | Was modelled and written by nothing, so a slot (a `users.id`) and a released result (a `trainees.id`) were two unconnected records for one person. Rostering links an existing account, and registering claims the entries waiting for it |
| The last five oracles | Feedback model parity, engine schema parity, JWT claims and default workspace, cohort scoring arithmetic and the Stripe receipt are ported. The legacy marking schemas and prompts are captured into `tests/fixtures/`, so the parity tests no longer depend on the sibling checkouts being present — which is what they would have lost the day those repos are deleted |
| Invitations | Naming somebody by email is inviting them. A membership or a roster row for an address with no account used to be refused or left unlinked, so nobody could be put on a circuit until they happened to register unprompted |
| A lapsed subscriber could still be read the material | Found by a security review of the material index, 2026-09-18, and it predates it: `domain.entitled_exam_ids` read `exam_id` off **every** grant. `entitlements.service.list_for_user` deliberately returns every row a person has ever held — revoking sets `revoked_at` and leaves the row — and computes `live` per row rather than filtering, so the gate handed a revoked or expired subscriber exactly what a paying one got. It gated `suggest_material` only until the material index landed; then it became the `WHERE exam_id IN (...)` behind the tutor's reading too, so an expired subscriber would have been read paid management plans aloud, with citations, indefinitely. Now filters on `live`, and **fails closed** on a grant that cannot say — a caller passing raw rows gets nothing rather than everything. A contract test revokes a live entitlement mid-session and asserts the tutor stops |
| The tutor can answer a clinical question | `search_material` used to say it was not configured, so the tutor knew a doctor's own history and could not answer "how do I safety-net chest pain" — which is the question they actually ask it. The study material is now a pgvector index in this same database (ADR 0019): `material_chunks`, a nightly `reindex_material` job and an admin route, with the chunker a byte-for-byte port of b2c's pinned by an oracle. The entitled exams are a `WHERE` applied **before** the ranking, so a doctor cannot be read out of material they have not bought — the A to Z and the slides are now gated on these routes too — they used to come back in full to anybody who asked, with no token at all on the listing. A deployment with no embedding key has no index and says it cannot look something up, rather than saying the material does not cover it |
| The exam clock (D-6) | Server-owned. Switching the turn starts the reading phase, dispatching starts the simulation, and either takes the clock off the previous slot; it used to live in the supervisor's browser and was lost on refresh |

## Not built

- **The receipt document.** The fields are minted with the payment and read back
  through `/me/receipts`; nothing renders or emails one. That is the remaining
  half of the fifth oracle — `b2c-api/b2c/tests/unit/test_receipt_document.py`
  is the byte-level oracle for it.
- **Station sets, sittings and org data in the migration.** The consumer path —
  people, entitlements, attempts, transcripts, legacy feedback — is end to end;
  the rest is not transformed.

## Two things not to take on trust

**The e2e test passed for the first time on 2026-09-18.** The real assessment
worker joined a real LiveKit room, bootstrapped against a locally running
platform-api, and the completed transcript came back through `GET
/attempts/{id}/transcript`. One run, one station (`sca`), on a local API — not
CI, and not against a deployed one.

**The dashboard e2e case is written and has never been run.** `tests/e2e/
test_dashboard_e2e.py` covers the other worker and the route the whole tutor
hangs off: a dashboard session is opened, a browser mints a token for its room,
the real *assistant* worker joins, and the bootstrap it is handed is asserted to
carry the tutor's four tools with their schemas — an empty list there is the
pre-tutor behaviour and passes every other test in the suite. A tool call and
the summarise-then-delete promise are exercised too.

What it deliberately does **not** assert is that the model chose to call a tool.
That depends on what the candidate's audio happens to say and on the model's
judgement that day, and a test that fails when a model judges differently is a
test that gets deleted. The tool route is exercised directly instead, exactly as
the worker calls it; the `assistant tool call` log line records what the model
actually did, with the round trip in milliseconds.

The first run was worth as much as the plan hoped: it found three defects in
the test itself, all of which had been invisible.

- It imported the worker's harness as `tests.e2e._harness`, and *this*
  repository has a package of that name, so the import found ours and failed.
  It is loaded from its file now, and registered in `sys.modules` before it is
  executed — the harness declares dataclasses, and `dataclasses` resolves
  annotations through `sys.modules[cls.__module__]`.
- It started the worker on `sys.executable`, which is this API's interpreter
  and has no `livekit-agents`. The subprocess died on import, and the assertion
  saw only an attempt with no turns. `ASSESSMENT_PLATFORM_PYTHON` now points at
  the worker's own environment.
- Running it needs data nothing seeds: a published exam with a rubric, a
  published library station and an entitled candidate. The exam in a fresh
  local database is a draft with no rubric, so the attempt is refused with
  `unknown_exam`.

The harness also needs `aiohttp` and the **realtime** `livekit` SDK, which are
`assessment-platform`'s dev dependencies and not this API's (we declare
`livekit-api`, which is a different package). Install them into the test
environment before running and **uninstall them afterwards**: the realtime SDK
drags in `numpy`, whose type stubs need Python 3.12, and `make typecheck` runs
mypy at 3.11 and stops on the first syntax error in them.

**`poetry run pytest -q | tail -2` reports the last two lines and not the exit
code**, so a red suite can look green. That led to two commits with failing
tests. Use `make test`, or check `$?`.

## Running it

```bash
make db-up && make migrate && make start     # http://localhost:8002/docs
make engine-dev                              # install osce_assessment editable
make ci                                      # lint, mypy, import-linter, tests
make guards                                  # architecture rules alone
python scripts/status_report.py --check      # is this document still true?
```

## What to read first

1. `docs/HANDOVER.md` — if you are picking this up cold.
2. `docs/adr/` — 0010 to 0013 are the decisions behind the current shape.
3. `docs/OPEN-QUESTIONS.md` — what needs a human answer.

<!-- generated: do not edit below this line -->

_Generated by `scripts/status_report.py`. Do not edit below the marker; run `make status`._

**318 operations across 274 paths. 29 slices. 46 migrations.**

## Slices

| Slice | App lines | Domain rules | Unwired | Routes |
|---|---|---|---|---|
| `assistant` | 1236 | 4 | — | 6 |
| `attempts` | 4707 | 21 | is_terminal, required_reference | 22 |
| `billing` | 2032 | 4 | — | 6 |
| `catalog` | 1276 | 6 | — | 0 |
| `community` | 947 | 3 | — | 9 |
| `cv` | 523 | 2 | — | 3 |
| `dashboard` | 2742 | 0 | — | 2 |
| `entitlements` | 1050 | 3 | — | 8 |
| `generation` | 447 | 0 | — | 0 |
| `growth` | 835 | 6 | — | 5 |
| `health` | 399 | 0 | — | 2 |
| `identity` | 2271 | 6 | — | 0 |
| `marketplace` | 1046 | 4 | — | 5 |
| `media` | 1008 | 8 | — | 12 |
| `media_production` | 2990 | 1 | — | 0 |
| `notifications` | 472 | 4 | — | 0 |
| `peer_practice` | 1844 | 2 | — | 4 |
| `public_site` | 438 | 3 | — | 0 |
| `results` | 1059 | 7 | — | 2 |
| `reviews` | 1198 | 6 | — | 2 |
| `roster` | 1580 | 4 | — | 1 |
| `rubrics` | 2154 | 5 | — | 14 |
| `sittings` | 5015 | 23 | — | 14 |
| `sso` | 1067 | 7 | — | 5 |
| `station_sets` | 1017 | 4 | — | 7 |
| `stations` | 4062 | 3 | — | 24 |
| `tenancy` | 2550 | 11 | — | 0 |
| `tutor_memory` | 3377 | 8 | — | 4 |
| `voice` | 936 | 5 | — | 4 |

## Planned endpoints that do not exist

- `POST /api/v1/orgs/{org_slug}/feedback-templates/{template_id}/publish`
- `POST /api/v1/orgs/{org_slug}/circuits/{circuit_id}/switch-turn`
- `POST /api/v1/orgs/{org_slug}/circuits/{circuit_id}/dispatch-agent`
- `POST /api/v1/orgs/{org_slug}/circuits/{circuit_id}/end-consultation`
- `GET /api/v1/partners/{partner}/report`

## Domain rules with no production caller

Each is listed in `tests/guards/test_domain_rules_are_reachable.py` with a reason.
The guard fails if this list grows, and fails if an entry becomes reachable and is
left here.

- `attempts.is_terminal` — helper; status checks compare the enum directly
- `attempts.required_reference` — the CHECK constraint enforces this; the rule mirrors it
