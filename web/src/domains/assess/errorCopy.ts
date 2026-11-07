import { errorMessage } from "@/foundation/hooks/useAsync";
import { isPlatformError, type PlatformErrorCode } from "@/foundation/platform-client";
import { aOrAn, INSTITUTION_WORDS, type AssessWords } from "@/domains/assess/vocabulary";

/**
 * Plain words for the codes the decision, review, sitting, circuit and roster screens can meet
 * (EXPERIENCE-GAPS section 11), worded for the workspace: an institution says sitting, trainee,
 * circuit and cohort, an employer says assessment, candidate, rotation and intake. Keyed by code,
 * never by the server's sentence; a code with no entry shows the server's own message, and a typo
 * in a key fails the type check.
 */
function assessErrorCopy(w: AssessWords): Partial<Record<PlatformErrorCode, string>> {
  const { sitting, trainee, circuit, circuits, cohort, supervisor } = w;
  const sittingA = aOrAn(sitting);
  return {
    // decisions and results
    evidence_changed: "The marking changed after this was signed off. Review it and sign it off again before releasing.",
    decision_revised: "Somebody else changed this decision. Reload it and check it before saving again.",
    invalid_workflow: "This decision is not in the right stage for that. It must be signed off, and not yet released.",
    not_signable: "This decision cannot be signed off yet. Choose an outcome and write the reason first.",
    incompatible_outcomes: "That outcome and the hiring outcome do not go together. Change one of them.",
    recruitment_outside_exam: w.hiring
      ? "A hiring outcome can only be recorded on a formal exam assessment."
      : "A hiring outcome can only be recorded on an exam sitting.",
    result_not_released: "This result has not been released to the candidate yet.",
    result_not_found: "No decision has been recorded for this candidate yet.",
    decision_outside_exam: w.hiring
      ? "Decisions are recorded for formal exam assessments only"
      : "Decisions are recorded for exam-mode sittings only",
    candidate_did_not_sit: `This candidate did not sit any station on this ${sitting}`,
    outcome_not_releasable: "A withheld or inconclusive outcome cannot be released",
    not_an_exam_sitting: w.hiring
      ? "An intake summary is only produced for a formal exam assessment"
      : "A cohort summary is only produced for an exam sitting",
    // reviews
    review_conflict: "Another reviewer saved since you opened this. Load theirs before saving.",
    review_incomplete: "Rate every required area before completing the review.",
    nothing_to_review: "Nobody took this station, so there is nothing to review.",
    invalid_review_status: "A review can only be saved as a draft or completed.",
    reviews_pending: "A review of this candidate's stations is still a draft. Complete it, or ask its author to withdraw it, then sign off.",
    review_not_draft: "Only a draft review can be withdrawn. A completed review is edited instead.",
    review_not_found: "That review no longer exists. Reload the page.",
    invalid_rating: "One of the ratings is not one this station accepts. Pick again from the list.",
    review_locked: "This candidate's result has been signed off or released, so its reviews can no longer be changed",
    not_slot_reviewer: `Only the ${supervisor} named on this ${circuit}, or an administrator, can review it`,
    circuit_review_finalized: `This ${circuit}'s review has already been finalised`,
    // sittings and circuits
    circuit_locked: `This ${circuit} has started or has feedback recorded, so its stations can no longer be changed. Reload to see where it is now.`,
    sitting_locked: `${aOrAn(circuit, true)} on this ${sitting} has started, so it cannot be cancelled. End its ${circuits} instead.`,
    stale_revision: `This ${circuit} changed since you opened it. Reload to see the latest.`,
    invalid_circuit: `This ${circuit} cannot be built as set up. Check the stations, ${w.trainees} and timings.`,
    circuit_not_found: `This ${circuit} no longer exists. It may have been deleted.`,
    circuit_not_started: `The ${circuit} has not been started yet.`,
    circuit_not_live: `The ${circuit} is not running, so nothing can be sat on it now.`,
    circuit_paused: `The ${circuit} is paused. Resume it first.`,
    circuit_not_paused: `The ${circuit} is not paused.`,
    circuit_already_ended: `The ${circuit} has already ended.`,
    not_a_training_circuit: `Only a practice ${circuit} has a room to manage. An exam keeps its own rules.`,
    circuit_not_ended: `End the ${circuit} first. The room can only be closed after it has ended.`,
    peer_marks_not_allowed: `Marking another ${trainee} is only part of practice ${circuits}.`,
    peer_marks_own_turn: "You cannot mark your own turn.",
    peer_marks_closed: "This turn is no longer open for marks.",
    peer_mark_item_unknown: "That item is not in this station's marking scheme.",
    peer_mark_rating_unknown: "That rating is not one of Met, Partly or Not met.",
    review_already_completed: "This review has already been released, so a live mark cannot change it.",
    scheme_not_shown: `The marking scheme is not shown for this ${circuit}.`,
    no_active_station: `No station is being sat on this ${circuit} right now.`,
    sitting_not_found: `This ${sitting} no longer exists. It may have been deleted.`,
    slot_not_found: `That place on the ${circuit} no longer exists. Reload the page.`,
    programme_required: `Choose a programme for this ${sitting} first.`,
    programme_exists: "A programme with that name already exists.",
    programme_not_found: "That programme no longer exists. Reload the page.",
    rubric_not_found: "This station has no marking scheme, so it cannot be marked.",
    rubric_version_not_found: "The marking scheme for this station is missing a version. Ask the station's owner to republish it.",
    exam_rubric_not_ready: "That programme's exam is not ready to mark against yet",
    lead_cannot_run: w.hiring
      ? `${aOrAn(circuit, true)}'s lead must be a lead assessor or assessor of this organisation`
      : `A ${circuit}'s lead must be an administrator or ${supervisor} of this organisation`,
    trainee_already_on_circuit: `That person is already on this ${circuit}`,
    station_not_on_circuit: `That station is not on this ${circuit}`,
    not_permitted_in_mode: `That action does not apply to this kind of ${circuit}`,
    // roster
    trainee_exists: `That person is already on your ${trainee} list.`,
    trainee_revoked: `That person's access has been removed. Restore them before adding them to ${sittingA}.`,
    trainee_not_found: `That ${trainee} is no longer on your list.`,
    trainee_not_on_roster: `That person is not on your ${trainee} list. Add them first.`,
    trainee_in_use: `That ${trainee} is on ${sittingA}, so they cannot be deleted. Remove their access instead.`,
    too_many_trainees: `An import takes at most 500 ${w.trainees} at a time`,
    cohort_exists: `${aOrAn(cohort, true)} with that name already exists.`,
    cohort_not_found: `That ${cohort} no longer exists.`,
    cohort_in_use: `That ${cohort} is on ${sittingA}, so it cannot be deleted.`,
    group_exists: "A group with that name already exists.",
    group_not_found: "That group no longer exists.",
    // team
    membership_exists: "That person is already on the team.",
    last_admin: w.hiring
      ? "This is the organisation's last lead assessor. Make someone else a lead assessor first"
      : "This is the organisation's last administrator. Make someone else an administrator first",
    invitation_not_pending: "That invitation has already been accepted or withdrawn.",
    not_a_member: "You are not a member of this organisation.",
  };
}

/** What to tell a person for a failed decision, review, sitting, circuit or roster action. */
export function assessErrorMessage(cause: unknown, words: AssessWords = INSTITUTION_WORDS): string {
  if (isPlatformError(cause)) {
    const copy = assessErrorCopy(words)[cause.code];
    if (copy) return copy;
  }
  return errorMessage(cause);
}
