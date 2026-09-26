import type { PILOT_EXAMS, PILOT_PARTNERS } from "./partnerConstants";

export type PilotExam = (typeof PILOT_EXAMS)[number];
export type PilotPartner = (typeof PILOT_PARTNERS)[number];

export type ParsedReferralParams = {
  partner: PilotPartner;
  exam: PilotExam;
  utmMedium: string | null;
  utmCampaign: string | null;
  refId: string | null;
  /** Path + query string for ledger persistence (e.g. ``/exams/sca?utm_source=bmj``). */
  landingPath: string;
};

export type BuildReferralUrlInput = {
  /** Partner slug — must match `utm_source` (defaults to BMJ). */
  partner?: PilotPartner;
  exam: PilotExam;
  utmMedium?: string;
  utmCampaign?: string;
  refId?: string;
  /**
   * When true (default), build ``https://{exam}.<site-host>/`` — the exam
   * subdomain of this deployment's own site (see
   * ``foundation/config/siteUrl.ts``: production's host, or staging's).
   * When false, build ``https://www.<site-host>/exams/{exam}``.
   */
  useExamSubdomain?: boolean;
  /** Base origin without trailing slash (defaults to this deployment's own ``https://www.<site-host>``). */
  origin?: string;
};
