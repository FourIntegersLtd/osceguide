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
/*
 * The retiring client nested these under `/auth`. There is one sign-in for
 * every product now, so they sit at the root beside the landing — see ADR
 * 0002. Every call site reaches them through `partner.href`, so this is the
 * only place the spelling lives.
 */
export const REGISTER_PATH = "/register";
export const LOGIN_PATH = "/login";

/*
 * The visitor's own key, and how long we keep claiming they had one.
 *
 * The retiring client also set a signed `osce_acquisition` cookie, issued by
 * the old backend so the edge could not invent an attribution. platform-api
 * asks for no signature — an arrival and a signup both carry an opaque
 * `visitor_key` — so the signature had no counterpart to talk to and the second
 * cookie went with it. One value, one name, and `arrivalCapture.ts` says why it
 * is readable by the browser.
 */
export const VISITOR_KEY_COOKIE_NAME = "osce_visitor_key";

/** First-touch lifetime (days). A partner's credit outlives the campaign. */
export const VISITOR_KEY_COOKIE_MAX_AGE_DAYS = 90;

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
