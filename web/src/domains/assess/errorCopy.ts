import { errorMessage } from "@/foundation/hooks/useAsync";
import type { AssessWords } from "@/capabilities/assess-words";
import { isPlatformError, type PlatformErrorCode } from "@/foundation/platform-client";

/**
 * Plain words for the codes the decision, review, sitting, circuit and roster screens can meet
 * (EXPERIENCE-GAPS section 11). Keyed by code, never by the server's sentence; a code with no entry
 * shows the server's own message, and a typo in a key fails the type check.
 */
/** The institution's lines, kept as they were; an employer reads `hireCopy`. */
const INSTITUTION_COPY: Partial<Record<PlatformErrorCode, string>> = {
  // decisions and results
  evidence_changed: "The marking changed after this was signed off. Review it and sign it off again before releasing.",
  decision_revised: "Somebody else changed this decision. Reload it and check it before saving again.",
  invalid_workflow: "This decision is not in the right stage for that. It must be signed off, and not yet released.",
  not_signable: "This decision cannot be signed off yet. Choose an outcome and write the reason first.",
  decisions_incomplete: "Every candidate needs a decision before the results can be signed off.",
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

function hireCopy(w: AssessWords): Partial<Record<PlatformErrorCode, string>> {
  return {
    // decisions and results
    evidence_changed: "The marking changed after this was signed off. Review it and sign it off again before releasing.",
    decision_revised: "Somebody else changed this decision. Reload it and check it before saving again.",
    invalid_workflow: "You can only do this after the decision is signed off and before it is released. Check where this decision is up to.",
    not_signable: "This decision cannot be signed off yet. Choose an outcome and write the reason first.",
    decisions_incomplete: `Every ${w.trainee} needs a hiring decision before the results can be signed off.`,
    incompatible_outcomes: `The result and the hiring decision contradict each other (for example, Fail with ${w.hiring ? "Hired" : "Hire"}). Change one so they agree.`,
    recruitment_outside_exam: "Hiring decisions can only be recorded for a formal exam, not for training. Remove the hiring decision.",
    result_not_released: "This result has not been released to the candidate yet.",
    result_not_found: "No result has been decided for this candidate yet. Open the candidate and sign off a decision first.",
    // reviews
    review_conflict: "Another reviewer saved since you opened this. Load theirs before saving.",
    review_incomplete: "Rate every required area before completing the review.",
    nothing_to_review: "Nobody sat this station, so there is nothing to review. You can move on to the next one.",
    invalid_review_status: "Something went wrong saving this review. Reload the page and try again.",
    reviews_pending: "A review of this candidate's stations is still a draft. Complete it, or ask its author to delete the draft, then sign off.",
    review_not_draft: "Only a draft review can be deleted. A completed review is edited instead.",
    review_not_found: "That review no longer exists. Reload the page.",
    invalid_rating: "One of your ratings is not available for this station. Choose a rating from the list again.",
    // sittings and circuits
    circuit_locked: `This ${w.circuit} has already started or has feedback, so its stations cannot be changed now. Reload the page to see where it is up to.`,
    sitting_locked: `This ${w.sitting} has already started, so it cannot be cancelled. End each running ${w.circuit} instead.`,
    stale_revision: `Someone else changed this ${w.circuit} while you were looking at it. Reload the page, then make your change again.`,
    invalid_circuit: `This ${w.circuit} cannot be created yet. Check that every candidate has a station and the timings make sense.`,
    circuit_not_found: `This ${w.circuit} no longer exists. It may have been deleted.`,
    circuit_not_started: `The ${w.circuit} has not been started yet.`,
    circuit_not_live: `The ${w.circuit} is not running, so nobody can sit a station on it. Start it first.`,
    circuit_paused: `The ${w.circuit} is paused. Resume it first.`,
    circuit_not_paused: `The ${w.circuit} is not paused.`,
    circuit_already_ended: `The ${w.circuit} has already ended.`,
    not_a_training_circuit: `Only a practice ${w.circuit} has a room to manage. An exam keeps its own rules.`,
    circuit_not_ended: `End the ${w.circuit} first. The room can only be closed after it has ended.`,
    peer_marks_not_allowed: `Marking another ${w.trainee} is only part of practice ${w.circuits}.`,
    peer_marks_own_turn: "You cannot mark your own turn.",
    peer_marks_closed: "This turn is no longer open for marks.",
    peer_mark_item_unknown: "That item is not in this station's marking scheme.",
    peer_mark_rating_unknown: "That rating is not one of Met, Partly or Not met.",
    review_already_completed: "This review has already been released, so a live mark cannot change it.",
    scheme_not_shown: `The marking scheme is not shown for this ${w.circuit}.`,
    no_active_station: `No station is running on this ${w.circuit} at the moment. Start the ${w.circuit} or move to the next station.`,
    sitting_not_found: `This ${w.sitting} no longer exists. It may have been deleted.`,
    slot_not_found: `That turn on the ${w.circuit} was removed. Reload the page to see the current list.`,
    programme_required: `Choose an exam for this ${w.sitting} first.`,
    programme_exists: "An exam with that name already exists.",
    rubric_not_found: "This station has no marking scheme, so it cannot be marked. Ask the station's author to publish one.",
    rubric_version_not_found: "This station's marking scheme is out of date or incomplete. Ask whoever wrote the station to publish it again.",
    // roster
    trainee_exists: `That person is already on your ${w.trainee} list.`,
    trainee_revoked: `This person's access was switched off. Switch it back on in the ${w.trainee} list, then add them to the ${w.sitting}.`,
    trainee_not_found: `That ${w.trainee} is no longer on your list.`,
    trainee_not_on_roster: `That person is not on your ${w.trainee} list. Add them first.`,
    cohort_exists: `${w.hiring ? "An intake" : "A cohort"} with that name already exists.`,
    cohort_not_found: `${w.hiring ? "That intake" : "That cohort"} no longer exists.`,
    group_exists: "A group with that name already exists.",
    group_not_found: "That group no longer exists.",
  };
}

/** What to tell a person for a failed decision, review, sitting, circuit or roster action. */
export function assessErrorMessage(cause: unknown, w: AssessWords): string {
  if (isPlatformError(cause)) {
    const copy = (w.hiring ? hireCopy(w) : INSTITUTION_COPY)[cause.code];
    if (copy) return copy;
  }
  return errorMessage(cause);
}
