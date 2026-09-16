# results

## Purpose
A candidate's outcome for a sitting, and the workflow that gets it to them.

Ported from b2b's `sql/017`, which is the best-modelled thing in either legacy
backend and is carried over rather than reinvented: append-only revisions
enforced by a trigger, an explicit workflow, a compatibility matrix between the
two outcomes, and an outbox rather than an inline email.

## Use cases
- As an **institution admin**, I record a decision and revise it.
- As an **institution admin**, I sign it off, with a rationale.
- As an **institution admin**, I release it to the candidate.
- As a **candidate**, I see my result once it is released, and not before.

## Aggregates & invariants
**CandidateResultRevision** is the root; events and notifications hang off it.

- Revisions and events are **append-only, enforced by a database trigger**. A
  correction is a new revision superseding the old, so what was considered
  survives and the record stays defensible months later.
- `draft → signed_off → released`. A draft cannot be released directly, and a
  released decision is final.
- Sign-off requires an assessment outcome **and** a rationale — somebody has to
  be able to say why, later, to a candidate or an appeal. Capped at 4000 characters.
- The two outcomes are checked against each other, so a failed candidate cannot
  be recorded as hired and an unresolved assessment leaves recruitment pending.
- Release re-checks the **evidence fingerprint**. A station re-marked between
  sign-off and release would otherwise send an outcome nobody approved.
- A candidate sees only released revisions, and a narrower shape: moderation
  notes and the evidence snapshot stay internal. b2b's own schema doc says not
  to reproduce disclosure policy in frontend transforms, so it is applied here.
- The notification is an outbox row, so a release is not lost because a mail
  provider was briefly down.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET/PUT | `.../sittings/{id}/candidates/{trainee_id}/decision` | institution admin | each save is a revision |
| POST | `.../decision/sign-off` | institution admin | `not_signable` (422) |
| POST | `.../decision/release` | institution admin | `evidence_changed` (409) |
| GET | `/api/v1/me/results/{sitting_id}` | bearer | released only |

## Jobs
Delivering the outbox is not yet written; the rows accumulate safely until it is.

## Cross-slice dependencies
None outward. Readiness — which sittings and scores count as evidence — is
assembled by the caller and hashed here.
