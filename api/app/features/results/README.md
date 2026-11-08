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
- As a **candidate** (or an administrator for them), I ask for a released result to be looked at again, with a reason.
- As an **institution admin**, I name a second marker for an appeal, or decline it with a reason.
- As an **institution admin**, I delete a candidate's data at their request; the marks and result history stay.

## Aggregates & invariants
**CandidateResultRevision** is the root; events and notifications hang off it.

- Revisions and events are **append-only, enforced by a database trigger**. A
  correction is a new revision superseding the old, so what was considered
  survives and the record stays defensible months later. The one update the
  trigger permits is erasure (S-20): `rationale` and `moderation_notes` become
  `[erased]` (`erase_text_for_user`, called by identity's erasure) and nothing
  else may change.
- **A draft save names the revision it was written from** (`expected_revision`,
  `0` for "nothing recorded yet"), and a stale one is refused with
  `decision_revised` (409). Append-only made a stale save *look* safe — no row
  was lost — while both administrators kept editing on a screen that no longer
  matched the database, and the revision that reached sign-off was whichever
  request landed last. The same rule already guarded the GP lead's review.
- `draft → signed_off → released`. A draft cannot be released directly, and a
  released decision is final. A signed-off decision goes back to draft by saving
  a draft over it (a new revision); there is no separate reopen route.
- `recruitment_outcome` is recorded only on an **exam-mode** sitting (hire is exam
  mode). A training sitting refuses one with `recruitment_outside_exam` (422). An employer org refuses `hired` with an empty rationale (`hire_reason_required`, 422) on save and sign-off.
- Sign-off requires an assessment outcome **and** a rationale — somebody has to
  be able to say why, later, to a candidate or an appeal. Capped at 4000 characters.
- The two outcomes are checked against each other, so a failed candidate cannot
  be recorded as hired and an unresolved assessment leaves recruitment pending.
- Release re-checks the **evidence fingerprint**. A station re-marked between
  sign-off and release would otherwise send an outcome nobody approved. The
  evidence is read by the server from the marking (`service_evidence`); the
  `evidence` a client posts is ignored.
- A `withheld` or `inconclusive` outcome can be signed off but not released
  (`outcome_not_releasable`, 409; a bulk release skips it with that code), and
  no "result available" email is queued for it.
- A candidate sees only released revisions, and a narrower shape: moderation
  notes and the evidence snapshot stay internal. b2b's own schema doc says not
  to reproduce disclosure policy in frontend transforms, so it is applied here.
- The notification is an outbox row, so a release is not lost because a mail
  provider was briefly down.

### Appeals (`service_appeals`)
- An appeal is asked against the candidate's **latest released revision**. One live appeal (`open` or
  `in_review`) per candidate and sitting, enforced by a partial unique index (`appeal_already_open`, 409).
- The second marker is an organisation administrator who **neither signed off nor released** the result
  under review (`second_marker_must_differ`, 422; `assignee_not_admin`, 422). Only the assigned marker may
  resolve (`not_assigned_marker`, 403).
- **Resolving appends a new `released` revision** superseding the one under review, even when the outcome is
  unchanged, so the history shows the review. The evidence snapshot is carried over: a re-mark of a station goes
  through the reviews slice first. An appeal whose result moved since it was asked is refused
  (`appeal_stale`, 409). Declining leaves the result alone. Both queue an email on the shared outbox
  (`candidate_result_revised`, `candidate_appeal_declined`) and write an audit row (`result_appeal.*`).
- A decided appeal is kept. Deleting a candidate's data scrubs its text to `[erased]`.

### Deleting a candidate's data (`service_candidate_erasure`)
- Irreversible and typed: the caller sends the candidate's address as on the roster
  (`confirmation_mismatch`, 422). Refused while an appeal is open (`appeal_open`, 409).
- Removes: transcripts of this candidate's attempts in this organisation (their marks stay), roster name and
  address (the existing anonymise), and the free text of their decisions and appeals (`[erased]`).
  Keeps: attempts, marks, every revision's outcome, signer and date. Does **not** touch the account (the
  person may sit elsewhere; the account has its own `/me` erasure), station-review notes, or the `payload`
  of a mark, which can quote the candidate.
- Repeating it is a no-op that writes no second audit row. One audit row: `candidate_data.erased`, with counts and no personal data.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET/PUT | `.../sittings/{id}/candidates/{trainee_id}/decision` | institution admin | each save is a revision; GET is 200 `null` before the first draft |
| POST | `.../decision/sign-off` | institution admin | `not_signable` (422), `evidence_changed` (409) |
| POST | `.../decision/release` | institution admin | `evidence_changed`, `outcome_not_releasable` (409) |
| GET | `/api/v1/me/results/{sitting_id}` | bearer | released only, with `acknowledged_at`; 200 `null` until released (the PDF and acknowledge still answer `result_not_released`) |
| POST | `/api/v1/me/results/{sitting_id}/acknowledge` | bearer | one event per revision; repeating returns the first answer |
| POST/GET | `/api/v1/me/results/{sitting_id}/appeal` | bearer | ask for a review (201) / read the newest one; `result_not_released` (404), `appeal_already_open` (409) |
| POST | `.../sittings/{id}/candidates/{trainee_id}/appeals` | institution admin | staff ask on the candidate's behalf |
| GET | `/api/v1/orgs/{slug}/appeals?decided=` | institution admin | the queue: waiting (default) or decided |
| POST | `.../appeals/{id}/assign` / `decline` / `resolve` | institution admin | `resolve` only by the assigned marker; `appeal_closed` (409) once decided |
| POST | `/api/v1/orgs/{slug}/candidates/{trainee_id}/erase-data` | institution admin | typed confirmation; see above |

## Jobs
Delivering the outbox is not yet written; the rows accumulate safely until it is.

## Cross-slice dependencies
`identity.service.user_refs_by_ids` (the second marker's name), `attempts.service_retention` (remove a candidate's
transcripts), `roster.service_edit.anonymise_trainee` (the existing erasure of name and address),
`tenancy.service.admin_user_ids` and `tenancy.service_audit` (who may be second marker; the audit row).
`sittings.service_reads.sitting_ref`, to learn a sitting's mode: a recruitment outcome is
only saved on an exam-mode sitting. Readiness — which sittings and scores count as evidence — is
assembled by the caller and hashed here.
