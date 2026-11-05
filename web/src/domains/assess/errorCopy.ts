import { errorMessage } from "@/foundation/hooks/useAsync";
import { isPlatformError, type PlatformErrorCode } from "@/foundation/platform-client";

/**
 * Plain words for the codes the decision, review, sitting, circuit and roster screens can meet
 * (EXPERIENCE-GAPS section 11). Keyed by code, never by the server's sentence; a code with no entry
 * shows the server's own message, and a typo in a key fails the type check.
 */
const ASSESS_ERROR_COPY: Partial<Record<PlatformErrorCode, string>> = {
  // decisions and results
  evidence_changed: "The marking changed after this was signed off. Review it and sign it off again before releasing.",
  decision_revised: "Somebody else changed this decision. Reload it and check it before saving again.",
  invalid_workflow: "This decision is not in the right stage for that. It must be signed off, and not yet released.",
  not_signable: "This decision cannot be signed off yet. Choose an outcome and write the reason first.",
  incompatible_outcomes: "That outcome and the hiring outcome do not go together. Change one of them.",
  recruitment_outside_exam: "A hiring outcome can only be recorded on an exam sitting.",
  result_not_released: "This result has not been released to the candidate yet.",
  result_not_found: "No decision has been recorded for this candidate yet.",
  // reviews
  review_conflict: "Another reviewer saved since you opened this. Load theirs before saving.",
  review_incomplete: "Rate every required area before completing the review.",
  nothing_to_review: "Nobody took this station, so there is nothing to review.",
  invalid_review_status: "A review can only be saved as a draft or completed.",
  reviews_pending: "A review of this candidate's stations is still a draft. Complete it, or ask its author to withdraw it, then sign off.",
  review_not_draft: "Only a draft review can be withdrawn. A completed review is edited instead.",
  review_not_found: "That review no longer exists. Reload the page.",
  invalid_rating: "One of the ratings is not one this station accepts. Pick again from the list.",
  // sittings and circuits
  circuit_locked: "This circuit has started or has feedback recorded, so its stations can no longer be changed. Reload to see where it is now.",
  sitting_locked: "A circuit on this sitting has started, so it cannot be cancelled. End its circuits instead.",
  stale_revision: "This circuit changed since you opened it. Reload to see the latest.",
  invalid_circuit: "This circuit cannot be built as set up. Check the stations, candidates and timings.",
  circuit_not_found: "This circuit no longer exists. It may have been deleted.",
  circuit_not_started: "The circuit has not been started yet.",
  circuit_not_live: "The circuit is not running, so nothing can be sat on it now.",
  circuit_paused: "The circuit is paused. Resume it first.",
  circuit_not_paused: "The circuit is not paused.",
  circuit_already_ended: "The circuit has already ended.",
  no_active_station: "No station is being sat on this circuit right now.",
  sitting_not_found: "This sitting no longer exists. It may have been deleted.",
  slot_not_found: "That place on the circuit no longer exists. Reload the page.",
  programme_required: "Choose a programme for this sitting first.",
  programme_exists: "A programme with that name already exists.",
  rubric_not_found: "This station has no marking scheme, so it cannot be marked.",
  rubric_version_not_found: "The marking scheme for this station is missing a version. Ask the station's owner to republish it.",
  // roster
  trainee_exists: "That person is already on your trainee list.",
  trainee_revoked: "That person's access has been removed. Restore them before adding them to a sitting.",
  trainee_not_found: "That trainee is no longer on your list.",
  trainee_not_on_roster: "That person is not on your trainee list. Add them first.",
  cohort_exists: "A cohort with that name already exists.",
  cohort_not_found: "That cohort no longer exists.",
  group_exists: "A group with that name already exists.",
  group_not_found: "That group no longer exists.",
};

/** What to tell a person for a failed decision, review, sitting, circuit or roster action. */
export function assessErrorMessage(cause: unknown): string {
  if (isPlatformError(cause)) {
    const copy = ASSESS_ERROR_COPY[cause.code];
    if (copy) return copy;
  }
  return errorMessage(cause);
}
