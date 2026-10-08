import { PlatformError } from "@/foundation/platform-client";

/**
 * The server's own sentence when it sent one, else the retiring client's
 * fallback for that action — which is what its `getErrorMessage(err, fallback)`
 * did. A dropped connection gets the fallback rather than a transport message.
 */
export function failureText(cause: unknown, fallback: string): string {
  return cause instanceof PlatformError && cause.message ? cause.message : fallback;
}

/** Refusals to join the queue whose own sentence says what to do next; retrying changes nothing. */
const JOIN_REFUSALS: ReadonlySet<string> = new Set([
  "not_entitled",
  "unknown_exam",
  "no_stations_for_exam",
]);

/** What the join toast says: the server's sentence for a refusal that retrying cannot fix. */
export function joinFailureText(cause: unknown): string {
  return cause instanceof PlatformError && JOIN_REFUSALS.has(cause.code)
    ? failureText(cause, "Please try again in a moment.")
    : "Please try again in a moment.";
}
