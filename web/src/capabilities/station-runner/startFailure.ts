import { hasCode, isPlatformError } from "@/foundation/platform-client";

/**
 * What to tell somebody whose attempt could not be created, by the code the API answered with.
 *
 * Never the server's own message for the codes below: `station_not_published` carries the
 * circuit builder's wording ("A circuit can only use a published station"), which means nothing
 * to a person who only pressed Start.
 */
export function describeStartFailure(cause: unknown): string {
  if (hasCode(cause, "not_entitled")) {
    const reason = isPlatformError(cause) ? cause.details?.reason : null;
    if (reason === "trial_exhausted") {
      return "Your free practice stations are used up. Ask your organisation for access, or subscribe, to keep practising.";
    }
    if (reason === "expired") {
      return "Your access to this exam has ended. Ask your organisation to renew it, or subscribe, to keep practising.";
    }
    return "You do not have access to this exam yet. Ask your organisation for access, or subscribe, to practise it.";
  }
  if (hasCode(cause, "station_not_published")) {
    return "This station is not available to practise right now. It may have been withdrawn or not finished yet.";
  }
  if (isPlatformError(cause)) return cause.message;
  return "We could not start this station. Please try again.";
}
