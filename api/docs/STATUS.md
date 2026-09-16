# Where the platform-api rewrite stands

One night's work, built to the method in `CONTRIBUTING.md`: use cases, then
guard and contract tests, then oracles ported from the legacy suites, then the
domain, then storage, then the service and router. Every commit green.

## Built

**2,110 tests. 88 endpoints. 22 slices. 20 migrations.**

| Slice | State | Notes |
|---|---|---|
| `health` | complete | pre-existing |
| `identity` | complete | register, login, refresh with reuse detection, logout, password reset, change password, `/me` |
| `tenancy` | complete | orgs, memberships, workspace switch, audit, `/me/capabilities`, platform admin |
| `catalog` | complete | four seeded exams, org programmes |
| `stations` | complete | platform library + org authoring, versions, publish/archive lifecycle |
| `attempts` | complete | the shared core, worker contract, scoring job |
| `entitlements` | complete | one access predicate, free trial ported verbatim |
| `voice` | complete | LiveKit token, agent routing, Cloud overflow |
| `sittings` | complete | sittings → circuits → slots, start/switch-turn/end |
| `roster` | complete | trainees, cohorts, groups **with a real membership table** |
| `reviews` | complete | slot rubric, GP-lead revisions, circuit aggregate — b2b's one table split three ways |
| `results` | complete | append-only revisions, sign-off, release, outbox; trigger-enforced |
| `billing` | routes done | Stripe webhook with idempotency ledger; **signature verification not wired** |
| `station_sets` | complete | consumer practice sets with attempt limits |
| `dashboard` | complete | read model replacing the seven-call home screen |
| `notifications` | complete | one outbox, backoff, abandon-after-six; identity and results write to it |
| `assistant` | routes done | both LiveKit workers can now target this backend; **content packs not ported** |
| `marketplace` | complete | offered slots, claimed once under a row lock |
| `community` | complete | questions, replies, station comments, real likes, real authorisation |
| `peer_practice` | complete | queue, fair role assignment, matching job |
| `growth` | complete | partner attribution, funnel, referrals; **Mixpanel reconciliation not ported** |
| `media` | complete | slides, summaries, blogs, podcasts, search behind a port; **generation not ported** |

## Not built

From the plan's phases, in rough priority order:

- **Phase 8's loader and verify step.** The *transforms* are written and tested
  as pure functions on realistic fixtures (`app/migration/`), including the
  five-record consumer merge. Loading and verification need a real export to be
  worth writing against.
- **Phase 9, frontend switchover.** Needs the backend domains it replaces.

## Wired to a port but not implemented

- **The evaluator.** `core.ports.Evaluator` fixes the boundary and a fake proves
  the scoring job against it. The real adapter needs `osce_assessment` as a
  versioned dependency rather than a vendored subtree (see OPEN-QUESTIONS E-1).
- **Stripe signature verification.** One middleware in front of an otherwise
  complete path (B-1). **Blocking for launch.**

## A habit worth keeping

`poetry run pytest -q | tail -2` reports the last two lines and **not** the exit
code, so a red suite can look green in a terminal. Twice during this work that
led to a commit with a failing test. Check `$?`, or use `make test`, which does.

## Running it

```bash
make db-up && make migrate && make start     # http://localhost:8002/docs
make test                                    # needs Docker
make guards                                  # architecture rules alone
```

## What to read first

1. `docs/adr/` — 0010 to 0013 are this session's decisions.
2. `docs/OPEN-QUESTIONS.md` — what needs your answer.
3. Any slice's `README.md` — use cases and invariants, in that order.
