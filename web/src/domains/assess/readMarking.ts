import { isPlatformError } from "@/foundation/platform-client";
import { readFeedback, type AttemptFeedbackRead } from "@/capabilities/feedback";

/**
 * The automatic marking beside a slot review. No marking yet (a 404) is an ordinary state next to a
 * review form, and so is a marking this person may not read (a 403, `hidden`): staff not named on
 * the circuit may review but not read it (R-26). Any other failure is a failure.
 */
export async function readMarking(
  attemptId: string | null,
  signal: AbortSignal,
): Promise<{ feedback: AttemptFeedbackRead | null; hidden: boolean }> {
  if (!attemptId) return { feedback: null, hidden: false };
  try {
    return { feedback: await readFeedback(attemptId, signal), hidden: false };
  } catch (err) {
    if (isPlatformError(err) && err.status === 403) return { feedback: null, hidden: true };
    if (isPlatformError(err) && err.status === 404) return { feedback: null, hidden: false };
    throw err;
  }
}
