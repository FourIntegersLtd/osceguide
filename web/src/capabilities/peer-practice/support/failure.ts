import { PlatformError } from "@/foundation/platform-client";

/**
 * What to tell somebody whose peer practice was refused for access. Peer practice is open to
 * a free trial for its two weeks and no longer, so the reason decides the wording; the server's
 * "You do not have access to this exam" says nothing about what to do next.
 */
function accessText(cause: PlatformError): string | null {
  if (cause.code !== "not_entitled") return null;
  const reason = cause.details?.reason;
  if (reason === "trial_expired") {
    return "Your free trial has ended, so peer practice is closed. Ask your organisation for access, or subscribe, to keep practising with others.";
  }
  if (reason === "expired") {
    return "Your access to this exam has ended. Ask your organisation to renew it, or subscribe, to keep practising with others.";
  }
  return "Peer practice needs access to this exam. Ask your organisation for access, or subscribe, to practise with others.";
}

/**
 * The server's own sentence when it sent one, else the retiring client's
 * fallback for that action — which is what its `getErrorMessage(err, fallback)`
 * did. A dropped connection gets the fallback rather than a transport message.
 * An access refusal gets its own wording (see `accessText`).
 */
export function failureText(cause: unknown, fallback: string): string {
  if (!(cause instanceof PlatformError)) return fallback;
  return accessText(cause) ?? (cause.message || fallback);
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
