import { getExamFromHost, resolvePilotExamFromHost } from "@/foundation/attribution/examFromHost";
import {
  EXAM_LANDING_PATH_PREFIX,
  PILOT_EXAMS,
  REF_ID_PARAM,
  UTM_PARAM_CAMPAIGN,
  UTM_PARAM_MEDIUM,
  UTM_PARAM_SOURCE,
  isPilotPartner,
} from "./partnerConstants";
import type { ParsedReferralParams, PilotExam } from "./partnerTypes";

const PILOT_EXAM_SET = new Set<string>(PILOT_EXAMS);

function normalizeOptional(value: string | null): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

function isPilotExam(value: string | null | undefined): value is PilotExam {
  return Boolean(value && PILOT_EXAM_SET.has(value));
}

function examFromPathname(pathname: string): PilotExam | null {
  const normalized = pathname.replace(/\/+$/, "") || "/";
  if (!normalized.startsWith(EXAM_LANDING_PATH_PREFIX)) {
    return null;
  }
  const remainder = normalized.slice(EXAM_LANDING_PATH_PREFIX.length);
  const exam = remainder.split("/")[0]?.toLowerCase();
  return isPilotExam(exam) ? exam : null;
}

function resolveExam(
  host: string | null | undefined,
  pathname: string,
): PilotExam | null {
  return resolvePilotExamFromHost(host) ?? examFromPathname(pathname);
}

function buildLandingPath(pathname: string, search: string): string {
  const path = pathname || "/";
  return search ? `${path}${search.startsWith("?") ? search : `?${search}`}` : path;
}

export type ParseReferralParamsInput = {
  host?: string | null;
  pathname: string;
  search?: string;
};

/**
 * Validate partner referral query params and resolve the pilot exam.
 *
 * Partner is read from ``utm_source`` and must be in ``PILOT_PARTNERS``.
 * Canonical contract: ``https://{exam}.<site-host>/?utm_source={partner}&...``
 * Fallback: ``https://www.<site-host>/exams/{exam}?utm_source={partner}&...``
 * where `<site-host>` is this deployment's own host — production's or
 * staging's — from ``foundation/config/siteUrl.ts``.
 */
export function parseReferralParams(
  input: ParseReferralParamsInput | URL,
): ParsedReferralParams | null {

  let host: string | null | undefined;
  let pathname: string;
  let searchParams: URLSearchParams;

  if (input instanceof URL) {
    host = input.host;
    pathname = input.pathname;
    searchParams = input.searchParams;
  } else {
    host = input.host;
    pathname = input.pathname;
    searchParams = new URLSearchParams(
      input.search?.startsWith("?") ? input.search.slice(1) : input.search ?? "",
    );
  }

  const utmSource = searchParams.get(UTM_PARAM_SOURCE)?.trim().toLowerCase();
  if (!isPilotPartner(utmSource)) {
    return null;
  }

  const exam = resolveExam(host, pathname);
  if (!exam) {
    return null;
  }

  const search = searchParams.toString();
  const landingSearch = search ? `?${search}` : "";

  return {
    partner: utmSource,
    exam,
    utmMedium: normalizeOptional(searchParams.get(UTM_PARAM_MEDIUM)),
    utmCampaign: normalizeOptional(searchParams.get(UTM_PARAM_CAMPAIGN)),
    refId: normalizeOptional(searchParams.get(REF_ID_PARAM)),
    landingPath: buildLandingPath(pathname, landingSearch),
  };
}

/** Re-export for middleware exam rewrite alignment. */
export { getExamFromHost };
