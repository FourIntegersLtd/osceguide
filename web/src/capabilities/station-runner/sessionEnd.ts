export type EndReason = "manual" | "timer" | null;

/**
 * What the screen does once the consultation has stopped:
 * - `next`: go straight to the next station; its feedback is made in the background.
 * - `none`: the button that ended it already navigates.
 * - `time-up`: tell the learner the clock ran out, then move on (feedback in the background).
 * - `mark`: wait on the marking modal; this is the last station, or the only one.
 * - `summary`: nothing was said, so there is nothing to mark.
 *
 * `reason` is why this screen ended it: `null` is the learner's own End button or the patient
 * hanging up.
 */
export type EndOutcome = "next" | "none" | "time-up" | "mark" | "summary";

export function endOutcome({
  reason,
  isLast,
  consulted,
}: {
  reason: EndReason;
  isLast: boolean;
  consulted: boolean;
}): EndOutcome {
  if (reason === "timer") {
    if (!isLast) return "time-up";
    return consulted ? "mark" : "summary";
  }
  if (isLast) return "mark";
  return reason === null ? "next" : "none";
}
