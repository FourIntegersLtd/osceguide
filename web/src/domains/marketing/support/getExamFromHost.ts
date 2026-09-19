import { PILOT_EXAMS } from "@/domains/marketing/support/partnerConstants";
import type { PilotExam } from "@/domains/marketing/support/partnerTypes";

const PROD_BASE_DOMAIN = "osceguide.com";
const LOCAL_BASE_DOMAIN = "lvh.me";
const IGNORED_SUBDOMAINS = new Set(["www", ""]);
const PILOT_EXAM_SET = new Set<string>(PILOT_EXAMS);

const getActiveBaseDomain = () =>
  process.env.NODE_ENV === "production" ? PROD_BASE_DOMAIN : LOCAL_BASE_DOMAIN;

function examFromHostname(hostname: string, baseDomain: string): string | null {
  if (hostname === baseDomain || hostname === `www.${baseDomain}`) {
    return null;
  }
  if (!hostname.endsWith(baseDomain)) {
    return null;
  }
  const labels = hostname.split(".");
  const baseLabelsCount = baseDomain.split(".").length;
  if (labels.length <= baseLabelsCount) {
    return null;
  }
  const subdomain = labels[0];
  if (IGNORED_SUBDOMAINS.has(subdomain)) {
    return null;
  }
  return subdomain;
}

export function getExamFromHost(host: string | null | undefined) {
  if (!host) {
    return null;
  }
  const hostname = host.split(":")[0]?.toLowerCase();
  if (!hostname) {
    return null;
  }

  const active = examFromHostname(hostname, getActiveBaseDomain());
  if (active) {
    return active;
  }

  const alternate =
    getActiveBaseDomain() === PROD_BASE_DOMAIN ? LOCAL_BASE_DOMAIN : PROD_BASE_DOMAIN;
  return examFromHostname(hostname, alternate);
}

/** Resolve a pilot exam slug from the request host, or null if not a pilot subdomain. */
export function resolvePilotExamFromHost(
  host: string | null | undefined,
): PilotExam | null {
  const exam = getExamFromHost(host);
  if (exam && PILOT_EXAM_SET.has(exam)) {
    return exam as PilotExam;
  }
  return null;
}
