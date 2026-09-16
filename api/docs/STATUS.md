# Where the platform-api rewrite stands

One night's work, built to the method in `CONTRIBUTING.md`: use cases, then
guard and contract tests, then oracles ported from the legacy suites, then the
domain, then storage, then the service and router. Every commit green.

## Built

**1,236 tests. 45 endpoints. 12 slices. 7 migrations.**

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
| `billing` | routes done | Stripe webhook with idempotency ledger; **signature verification not wired** |
| `station_sets` | complete | consumer practice sets with attempt limits |
| `dashboard` | complete | read model replacing the seven-call home screen |

## Not built

From the plan's phases, in rough priority order:

- **`reviews`** — human feedback: slot rubric, peer observer, GP-lead revisions,
  circuit aggregates. b2b's `b2b_feedback` split three ways.
- **`results`** — candidate result revisions, sign-off, release, outbox. Port
  `sql/017` wholesale; it is better than anything we would write.
- **`roster`** — trainees, cohorts, groups **with a real membership table**
  (b2b derives group membership by label-matching at circuit-build time).
- **`community`, `peer_practice`, `marketplace`** — b2c social.
- **`growth`, `media`, `assistant`, `notifications`** — partner attribution/BMJ,
  slides and podcasts, the assistant worker routes, Resend email.
- **Phase 8, the data migration.** Needs a Firestore export and the b2b database.
- **Phase 9, frontend switchover.** Needs the backend domains it replaces.

## Wired to a port but not implemented

- **The evaluator.** `core.ports.Evaluator` fixes the boundary and a fake proves
  the scoring job against it. The real adapter needs `osce_assessment` as a
  versioned dependency rather than a vendored subtree (see OPEN-QUESTIONS E-1).
- **Stripe signature verification.** One middleware in front of an otherwise
  complete path (B-1). **Blocking for launch.**

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
