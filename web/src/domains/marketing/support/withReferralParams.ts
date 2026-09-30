import {
  APP_TYPE_PARAM,
  REF_ID_PARAM,
  UTM_PARAM_CAMPAIGN,
  UTM_PARAM_CONTENT,
  UTM_PARAM_MEDIUM,
  UTM_PARAM_SOURCE,
} from "../../../foundation/attribution/partnerConstants";
import type { StoredPartnerContext } from "./partnerContextStorage";

const CARRIED_PARAMS = [
  UTM_PARAM_SOURCE,
  UTM_PARAM_MEDIUM,
  UTM_PARAM_CAMPAIGN,
  UTM_PARAM_CONTENT,
  REF_ID_PARAM,
] as const;

export interface WithReferralParamsOptions {
  /** Current `window.location.search` (or any query string). */
  search?: string | null;
  /** Fallback when the URL no longer carries the params (later page in the funnel). */
  context?: StoredPartnerContext | null;
  /** Adds `appType` when the href doesn't already set it. */
  appType?: string | null;
}

/**
 * Appends partner referral params (utm_*, ref_id) and optional appType to a
 * same-origin href so the funnel keeps attribution and exam context across
 * landing → register → login. External hrefs are returned unchanged.
 */
export function withReferralParams(
  href: string,
  { search, context, appType }: WithReferralParamsOptions = {},
): string {
  if (!href.startsWith("/") || href.startsWith("//")) return href;
  // `split` always yields a first piece, but the compiler cannot see it.
  const [pathAndQuery = href, hash] = href.split("#");
  const [path = pathAndQuery, existingQuery = ""] = pathAndQuery.split("?");
  const target = new URLSearchParams(existingQuery);
  const source = new URLSearchParams(
    search?.startsWith("?") ? search.slice(1) : (search ?? ""),
  );

  for (const key of CARRIED_PARAMS) {
    if (target.has(key)) continue;
    const fromUrl = source.get(key);
    if (fromUrl) target.set(key, fromUrl);
  }
  if (context && !target.has(UTM_PARAM_SOURCE)) {
    target.set(UTM_PARAM_SOURCE, context.partner);
    if (context.utmMedium) target.set(UTM_PARAM_MEDIUM, context.utmMedium);
    if (context.utmCampaign) target.set(UTM_PARAM_CAMPAIGN, context.utmCampaign);
    if (context.refId) target.set(REF_ID_PARAM, context.refId);
  }
  const selectedExam = appType || source.get(APP_TYPE_PARAM) || context?.exam;
  if (selectedExam && !target.has(APP_TYPE_PARAM)) target.set(APP_TYPE_PARAM, selectedExam);

  const query = target.toString();
  return `${path}${query ? `?${query}` : ""}${hash ? `#${hash}` : ""}`;
}
