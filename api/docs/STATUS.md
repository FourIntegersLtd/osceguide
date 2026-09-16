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
| End to end | Creation → bootstrap → chunks → transcript → scored result, over real routes, plus an e2e test against the real worker (**never run** — see below) |
| Reachability guard | Fires on a real planted orphan; ratchets a debt list that may only shrink |
| Tenant scoping guard | Was inspecting **zero** functions — it walked `ast.ClassDef` and matched SQL strings, neither of which exists since ADR 0013. Now inspects 41 |
| Cross-tenant write (P4) | Any org admin could store a review against any slot in the system. Reads filtered by org, so it looked contained |
| Org suspension | Was write-only: suspending an organisation restricted nobody |
| Free trial | Never ran, so no new consumer could start anything |
| S1 | A sitting could bind a draft rubric, or another org's |
| Cloud capacity | Counted for the first time, with b2c's scripts byte-identical; the two `livekit-cloud-slot` worker routes served |
| C4 | Row lock plus `ensure_live`. The race reproduced an ended circuit still showing a candidate consulting |
| C5, C6, C3, C8 | Agent dispatch with stale removal, a new attempt per dispatch, the edit lock, and appending latecomers into the live room |

## Not built

- **The four read models.** `/circuits/{id}/console`, `/orgs/{slug}/dashboard`,
  `/orgs/{slug}/supervisor/circuits` and `/me/sittings` do not exist. Without
  them the frontend keeps its N+1s and its 5- and 8-second polls, so the
  frontend switchover cannot remove them.
- **Feedback template authoring.** `FeedbackTemplateVersion` is referenced by
  nothing but its own model — no repository, no service, no routes — yet a
  sitting cannot be created without one. Today the only way to get a template
  version is to write one directly to the database.
- **The platform station library browse** (`GET /api/v1/stations`). Only
  org-scoped station routes exist.
- **Five of the twelve required oracles**: feedback model parity, engine schema
  parity, JWT claims and default membership, cohort scoring totals, Stripe
  receipt.
- **Station sets, sittings and org data in the migration.** The consumer path —
  people, entitlements, attempts, transcripts, legacy feedback — is end to end;
  the rest is not transformed.

## Two things not to take on trust

**The e2e test has never been run.** It needs a LiveKit project, Deepgram and
OpenAI keys, a sibling `assessment-platform` checkout and a live API. Writing it
caught a real bug in itself — it read `user_id` off a schema that does not carry
it — which is what an unrun test hides. Treat the first run as part of the test.

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

**110 operations across 94 paths. 22 slices. 20 migrations.**

## Slices

| Slice | App lines | Domain rules | Unwired | Routes |
|---|---|---|---|---|
| `assistant` | 572 | 4 | — | 4 |
| `attempts` | 1958 | 10 | is_terminal, required_reference | 9 |
| `billing` | 551 | 4 | — | 2 |
| `catalog` | 439 | 1 | — | 0 |
| `community` | 629 | 5 | apply_like, apply_unlike | 7 |
| `dashboard` | 175 | 0 | — | 1 |
| `entitlements` | 368 | 2 | — | 1 |
| `growth` | 646 | 5 | format_ref_id | 2 |
| `health` | 92 | 0 | — | 1 |
| `identity` | 929 | 5 | may_call | 0 |
| `marketplace` | 627 | 4 | — | 4 |
| `media` | 621 | 6 | — | 6 |
| `notifications` | 341 | 4 | is_due | 0 |
| `peer_practice` | 688 | 2 | — | 3 |
| `results` | 838 | 6 | — | 1 |
| `reviews` | 820 | 6 | combine_rag | 2 |
| `roster` | 748 | 5 | ensure_rosterable, memberships_from_labels | 1 |
| `sittings` | 1472 | 8 | ensure_editable | 8 |
| `station_sets` | 528 | 4 | — | 4 |
| `stations` | 932 | 9 | ensure_bindable, ensure_brief_editable, ensure_deletable, ensure_usable_in_circuit | 8 |
| `tenancy` | 831 | 9 | pick_default_workspace | 0 |
| `voice` | 711 | 5 | — | 1 |

## Planned endpoints that do not exist

- `GET /api/v1/stations`
- `POST /api/v1/orgs/{org_slug}/feedback-templates/{template_id}/publish`
- `POST /api/v1/attempts/{attempt_id}/abandon`
- `GET /api/v1/orgs/{org_slug}/circuits/{circuit_id}/console`
- `GET /api/v1/orgs/{org_slug}/dashboard`
- `GET /api/v1/orgs/{org_slug}/supervisor/circuits`
- `GET /api/v1/me/sittings`
- `GET /api/v1/partners/{partner}/report`
- `POST /api/v1/me/results/{sitting_id}/acknowledge`

## Domain rules with no production caller

Each is listed in `tests/guards/test_domain_rules_are_reachable.py` with a reason.
The guard fails if this list grows, and fails if an entry becomes reachable and is
left here.

- `attempts.is_terminal` — helper; status checks compare the enum directly
- `attempts.required_reference` — the CHECK constraint enforces this; the rule mirrors it
- `community.apply_like` — likes are counted in SQL, not recomputed in Python
- `community.apply_unlike` — as apply_like
- `growth.format_ref_id` — referral codes are generated in the service; unify or delete
- `identity.may_call` — rate limiting is not built yet
- `notifications.is_due` — the SKIP LOCKED claim query does the due check in SQL
- `reviews.combine_rag` — Phase D: the server should own RAG aggregation, not the browser
- `roster.ensure_rosterable` — Phase D
- `roster.memberships_from_labels` — import helper for the migration; move to app/migration
- `sittings.ensure_editable` — asserts C3; no structural-edit route to assert it at yet (edit_block reports it)
- `stations.ensure_bindable` — Phase D: T3 is not enforced
- `stations.ensure_brief_editable` — Phase D: T5, no brief-edit route
- `stations.ensure_deletable` — Phase D: no delete-version route
- `stations.ensure_usable_in_circuit` — Phase D: T4, a circuit may reference a draft station
- `tenancy.pick_default_workspace` — Phase C: login uses memberships[0] instead
