/** Shared partner attribution constants (mirror backend). */

export const UTM_PARAM_SOURCE = "utm_source";
export const UTM_PARAM_MEDIUM = "utm_medium";
export const UTM_PARAM_CAMPAIGN = "utm_campaign";
export const UTM_PARAM_CONTENT = "utm_content";
export const REF_ID_PARAM = "ref_id";
export const APP_TYPE_PARAM = "appType";

/**
 * Allowlisted `utm_source` values. To onboard a partner (e.g. NMC), add their slug here
 * and mirror in `backend/.../partner_attribution_constants.py` PILOT_PARTNERS.
 */
export const PILOT_PARTNERS = ["bmj"] as const;

export const PILOT_EXAMS = ["sca", "plab", "ortho"] as const;

/** Default when building links if `partner` is omitted. */
export const DEFAULT_PILOT_PARTNER: (typeof PILOT_PARTNERS)[number] = "bmj";

export const EXAM_LANDING_PATH_PREFIX = "/exams/";
export const REGISTER_PATH = "/auth/register";
export const LOGIN_PATH = "/auth/login";

export const ACQUISITION_COOKIE_NAME = "osce_acquisition";

/**
 * Non-httpOnly bridge so client Mixpanel can read `visitor_key` on the same
 * response as middleware `Set-Cookie` (httpOnly acquisition cookie is not
 * readable until the next request).
 */
export const VISITOR_KEY_BRIDGE_COOKIE_NAME = "osce_visitor_key";

/** First-touch acquisition cookie lifetime (days). */
export const ACQUISITION_COOKIE_MAX_AGE_DAYS = 90;

const PILOT_PARTNER_SET = new Set<string>(PILOT_PARTNERS);

export function isPilotPartner(
  value: string | null | undefined,
): value is (typeof PILOT_PARTNERS)[number] {
  return Boolean(value && PILOT_PARTNER_SET.has(value));
}

export function formatRefId(
  partner: (typeof PILOT_PARTNERS)[number],
  exam: (typeof PILOT_EXAMS)[number],
): string {
  return `${partner}-${exam}`;
}
