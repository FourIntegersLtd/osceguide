import { platformRequest, type components } from "@/foundation/platform-client";
import { readTranscript, type Transcript } from "@/capabilities/attempt-runner";

export type AssessmentResult = components["schemas"]["AssessmentResultRead"];
type ResultPage = components["schemas"]["Page_AssessmentResultRead_"];
export type AttemptFeedbackRead = components["schemas"]["AttemptFeedbackRead"];

export type { Transcript };
/** The transcript is `/attempts/{id}/transcript`, which the runner already owns. */
export { readTranscript };

/**
 * Every marking this attempt has.
 *
 * A page rather than one result, and deliberately so on the backend:
 * re-scoring under a new policy writes *beside* the old one so a candidate's
 * history stays readable. They arrive oldest first.
 *
 * An empty page is the normal state of a consultation that has just finished —
 * scoring is a background job — and not an error, which is why nothing here
 * turns it into one.
 */
export async function readResults(
  attemptId: string,
  signal?: AbortSignal,
): Promise<AssessmentResult[]> {
  const page = await platformRequest<ResultPage>(
    `/api/v1/attempts/${encodeURIComponent(attemptId)}/result`,
    { signal },
  );
  return page.items;
}

/**
 * Every marking of this attempt, with the rubric that says how to read it.
 *
 * `/attempts/{id}/feedback` pairs the results with the attempt's marking
 * rubric (its structure and resolved display) and each result's computed
 * totals, so the screen renders every exam the same way. `rubric` is null only
 * for an attempt marked before rubrics existed. Results arrive oldest first,
 * and an empty list is the normal state while marking is still running.
 */
export async function readFeedback(attemptId: string, signal?: AbortSignal): Promise<AttemptFeedbackRead> {
  return platformRequest<AttemptFeedbackRead>(
    `/api/v1/attempts/${encodeURIComponent(attemptId)}/feedback`,
    { signal },
  );
}

/**
 * The attempt's own stream, for a result that is still being marked.
 *
 * Marking is a background job of a minute or two. The retiring client met that
 * with an SSE hook, a reconciling poller on a back-off schedule and a ten
 * minute give-up timer, because its stream dropped events when nobody was
 * listening. The platform pushes the attempt itself until it is terminal.
 */
export function attemptStreamPath(attemptId: string): string {
  return `/api/v1/attempts/${encodeURIComponent(attemptId)}/stream`;
}

/** Scoring has finished, one way or the other. */
export function isTerminal(status: string): boolean {
  return status === "evaluated" || status === "failed";
}

/** A marking's date, for the picker that appears when an attempt has several. */
export function scoredAtLabel(result: { scored_at: string }): string {
  const date = new Date(result.scored_at);
  if (!Number.isFinite(date.getTime())) return "Unknown date";
  return date.toLocaleDateString("en-GB", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
