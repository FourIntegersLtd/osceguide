import { hasCode, isPlatformError } from "@/foundation/platform-client/errors";
import { isOrgSurface, type Surface } from "@/capabilities/surface";
import { plural } from "@/foundation/format";

/**
 * What to tell somebody the API refused, by the code (and, for access, the reason) it answered with.
 *
 * The one place every refusal is explained: starting a station, building a session, the library,
 * a peer queue. `not_entitled` carries why only in `details.reason` (`trial_exhausted`,
 * `expired`, `no_entitlement`), so a lapsed grant, a used-up trial and no access read differently.
 * Never the server's own message for the coded refusals: `station_not_published` carries the
 * circuit builder's wording, which means nothing to a person who only pressed Start.
 * `fallback` is what an unknown, non-API failure says. `surface` is where the person is: an institution's or employer's
 * person access is arranged by an administrator, so no refusal mentions a trial or buying.
 */
export const ORG_NO_ACCESS = "Your organisation hasn't given you access to this yet, so ask your administrator.";

export function describeRefusal(cause: unknown, fallback: string, surface?: Surface): string {
  if (surface && isOrgSurface(surface) && (hasCode(cause, "not_entitled") || hasCode(cause, "trial_station_limit"))) return ORG_NO_ACCESS;
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
  if (hasCode(cause, "trial_station_limit")) {
    const left = isPlatformError(cause) ? Number(cause.details?.stations_left ?? 0) : 0;
    if (left === 0) return "Your free trial has no stations left. Subscribe to add new stations.";
    return `Your free trial has ${plural(left, "station")} left. Choose ${left} or fewer new stations, or subscribe for more.`;
  }
  if (hasCode(cause, "set_locked")) {
    return "This session is locked because your access has ended. You can still review it.";
  }
  if (hasCode(cause, "station_not_published")) {
    return "This station is not available to practise right now. It may have been withdrawn or not finished yet.";
  }
  if (hasCode(cause, "station_exam_mismatch")) {
    return "This station is no longer part of this exam. Go back to your session and choose another.";
  }
  if (hasCode(cause, "station_not_in_plan")) {
    return "This station is not included in your plan. Upgrade to unlock it.";
  }
  if (hasCode(cause, "station_not_approvable")) {
    return "Only a published station can be approved. Publish it first.";
  }
  if (isPlatformError(cause)) return cause.message;
  return fallback;
}
